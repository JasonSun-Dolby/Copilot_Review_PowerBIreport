from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_find_exact_hist_logic_result.txt")

TARGET = {
    "0-1m": 0.7437746270164686,
    "1-5m": 0.20213734541915146,
    "5-10m": 0.024203360063663838,
    "10-15m": 0.008100716259766091,
    "15-20m": 0.004357014767998277,
    "20-25m": 0.002885370580337969,
    "25-30m": 0.0021900244186080354,
    "0.5-1h": 0.006976163064578965,
    "1-8h": 0.0051660344770954455,
    "8-24h": 0.00020327358195991655,
    ">24h": 0.000006070350371476338,
}

QUERY = """
WITH scenarios AS (
  SELECT 'stripped_all' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  UNION ALL
  SELECT 'stripped_all_ge2' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE duration_sec >= 2
  UNION ALL
  SELECT 'stripped_nov_may' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE DATE(TIMESTAMP_MICROS(event_timestamp)) >= DATE '2025-11-01'
    AND DATE(TIMESTAMP_MICROS(event_timestamp)) < DATE '2026-06-01'
  UNION ALL
  SELECT 'stripped_nov_may_ge2' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE DATE(TIMESTAMP_MICROS(event_timestamp)) >= DATE '2025-11-01'
    AND DATE(TIMESTAMP_MICROS(event_timestamp)) < DATE '2026-06-01'
    AND duration_sec >= 2
  UNION ALL
  SELECT 'stripped_cutoff_refresh' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-31 08:08:17+00'
  UNION ALL
  SELECT 'view_all' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
  UNION ALL
  SELECT 'view_all_ge2' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
  WHERE duration_sec >= 2
  UNION ALL
  SELECT 'view_nov_may' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
  WHERE DATE(TIMESTAMP_MICROS(event_timestamp)) >= DATE '2025-11-01'
    AND DATE(TIMESTAMP_MICROS(event_timestamp)) < DATE '2026-06-01'
  UNION ALL
  SELECT 'view_nov_may_ge2' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
  WHERE DATE(TIMESTAMP_MICROS(event_timestamp)) >= DATE '2025-11-01'
    AND DATE(TIMESTAMP_MICROS(event_timestamp)) < DATE '2026-06-01'
    AND duration_sec >= 2
  UNION ALL
  SELECT 'view_cutoff_refresh' AS scenario, event_timestamp, country, duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
  WHERE TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-31 08:08:17+00'
),
bins AS (
  SELECT
    scenario,
    CASE
      WHEN duration_sec < 60 THEN '0-1m'
      WHEN duration_sec < 300 THEN '1-5m'
      WHEN duration_sec < 600 THEN '5-10m'
      WHEN duration_sec < 900 THEN '10-15m'
      WHEN duration_sec < 1200 THEN '15-20m'
      WHEN duration_sec < 1500 THEN '20-25m'
      WHEN duration_sec < 1800 THEN '25-30m'
      WHEN duration_sec < 3600 THEN '0.5-1h'
      WHEN duration_sec < 28800 THEN '1-8h'
      WHEN duration_sec < 86400 THEN '8-24h'
      ELSE '>24h'
    END AS bin,
    COUNT(*) AS cnt
  FROM scenarios
  GROUP BY scenario, bin
),
tot AS (
  SELECT scenario, SUM(cnt) AS total_cnt
  FROM bins
  GROUP BY scenario
)
SELECT
  b.scenario,
  b.bin,
  b.cnt,
  SAFE_DIVIDE(b.cnt, t.total_cnt) AS pct
FROM bins b
JOIN tot t USING (scenario)
ORDER BY scenario,
CASE b.bin
  WHEN '0-1m' THEN 1
  WHEN '1-5m' THEN 2
  WHEN '5-10m' THEN 3
  WHEN '10-15m' THEN 4
  WHEN '15-20m' THEN 5
  WHEN '20-25m' THEN 6
  WHEN '25-30m' THEN 7
  WHEN '0.5-1h' THEN 8
  WHEN '1-8h' THEN 9
  WHEN '8-24h' THEN 10
  WHEN '>24h' THEN 11
  ELSE 99
END
"""


def main() -> None:
    c = bigquery.Client(project="ap3-prod-0e613121")
    rows = list(c.query(QUERY).result())

    by_scenario = {}
    for r in rows:
        by_scenario.setdefault(r.scenario, {})[r.bin] = float(r.pct)

    lines = []
    for scenario, vals in sorted(by_scenario.items()):
        sse = 0.0
        max_abs = 0.0
        for b, tv in TARGET.items():
            pv = vals.get(b, 0.0)
            d = pv - tv
            sse += d * d
            if abs(d) > max_abs:
                max_abs = abs(d)
        lines.append(f"scenario={scenario}\tsse={sse:.18g}\tmax_abs_diff={max_abs:.18g}")
        for b in TARGET:
            lines.append(
                f"  {b}\tpct={vals.get(b, 0.0):.18g}\tdelta={vals.get(b, 0.0)-TARGET[b]:.18g}"
            )

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
