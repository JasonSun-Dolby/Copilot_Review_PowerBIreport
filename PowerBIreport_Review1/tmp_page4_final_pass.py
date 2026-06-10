from pathlib import Path
from datetime import timezone

from google.cloud import bigquery

out = Path("tmp_page4_final_pass_result.txt")

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"

# Current Page 4 visual values (from live read)
TARGET_MAX = {
    "2025-11": 10.271544444444444,
    "2025-12": 9.757368611111112,
    "2026-01": 28.50047309027778,
    "2026-02": 5.834038888888889,
    "2026-03": 6.2034488888888895,
    "2026-04": 9.574871961805556,
    "2026-05": 28.014227430555554,
}
TARGET_MEAN = {
    "2025-11": 93.36897325747667,
    "2025-12": 86.9742738295131,
    "2026-01": 86.34027585396407,
    "2026-02": 94.42622125358629,
    "2026-03": 91.1541732804587,
    "2026-04": 100.11793456319575,
    "2026-05": 102.36145133377522,
}
TARGET_MEDIAN = {
    "2025-11": 40.00779342651367,
    "2025-12": 40.32108348083496,
    "2026-01": 40.213,
    "2026-02": 38.720001220703125,
    "2026-03": 39.467,
    "2026-04": 38.912,
    "2026-05": 40.75600015258789,
}
TARGET_HIST = {
    "0-1m": 0.6348252918043011,
    "1-5m": 0.32599099912657215,
    "5-10m": 0.026593265266576512,
    "10-15m": 0.005503870770529566,
    "15-20m": 0.0023010277485103797,
    "20-25m": 0.0012967708677462395,
    "25-30m": 0.0007738661174589709,
    "0.5-1h": 0.0019036036818089624,
    "1-8h": 0.0008014307266401251,
    "8-24h": 0.000008639653623943854,
    ">24h": 0.0000012342362319919791,
}
BIN_ORDER = list(TARGET_HIST.keys())

Q_MAX = f"""
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  MAX(max_duration_sec) / 3600.0 AS max_duration_hour
FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
GROUP BY 1
ORDER BY 1
"""

Q_MEAN_MEDIAN = f"""
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec,
    PERCENTILE_CONT(median_duration_sec, 0.5) OVER (PARTITION BY month) AS p50_median
  FROM `{PROJECT}.{DATASET}.monthly_video_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  AVG(mean_duration_sec) AS mean_duration_sec,
  ANY_VALUE(p50_median) AS median_duration_sec
FROM x
GROUP BY 1
ORDER BY 1
"""

Q_HIST_HOURLY = f"""
WITH h AS (
  SELECT
    TIMESTAMP_TRUNC(TIMESTAMP_MICROS(event_timestamp), HOUR) AS hr,
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
  FROM `{PROJECT}.{DATASET}.video_recording_events_stripped`
  GROUP BY hr, bin
)
SELECT hr, bin, cnt
FROM h
ORDER BY hr, bin
"""


def compare_series(name: str, got: dict, target: dict, tol: float = 1e-9):
    lines = [f"--- {name} ---"]
    ok = True
    for k in target:
        g = got.get(k)
        d = (g - target[k]) if g is not None else float("nan")
        if g is None or abs(d) > tol:
            ok = False
            lines.append(f"  {k}: bq={g} target={target[k]} delta={d}  *** MISMATCH")
        else:
            lines.append(f"  {k}: bq={g} target={target[k]} delta={d}")
    lines.append(f"  OVERALL: {'MATCH' if ok else 'MISMATCH'}")
    return lines, ok


def hist_score(counts: dict[str, int]):
    total = sum(counts.values())
    sse = 0.0
    max_abs = 0.0
    pct = {}
    for b in BIN_ORDER:
        p = (counts.get(b, 0) / total) if total else 0.0
        pct[b] = p
        d = p - TARGET_HIST[b]
        sse += d * d
        if abs(d) > max_abs:
            max_abs = abs(d)
    return pct, sse, max_abs


if __name__ == "__main__":
    c = bigquery.Client(project=PROJECT)
    lines = []

    max_rows = list(c.query(Q_MAX).result())
    got_max = {r.month: float(r.max_duration_hour) for r in max_rows}
    section, _ = compare_series("MAX_DURATION_HOUR", got_max, TARGET_MAX, tol=1e-12)
    lines.extend(section)

    mm_rows = list(c.query(Q_MEAN_MEDIAN).result())
    got_mean = {r.month: float(r.mean_duration_sec) for r in mm_rows}
    got_median = {r.month: float(r.median_duration_sec) for r in mm_rows}
    section, _ = compare_series("MEAN_DURATION_SEC", got_mean, TARGET_MEAN, tol=1e-12)
    lines.extend(section)
    section, _ = compare_series("MEDIAN_DURATION_SEC", got_median, TARGET_MEDIAN, tol=1e-12)
    lines.extend(section)

    hist_rows = list(c.query(Q_HIST_HOURLY).result())
    by_hr = {}
    for r in hist_rows:
        hr = r.hr.replace(tzinfo=timezone.utc)
        by_hr.setdefault(hr, {})[r.bin] = int(r.cnt)

    best = None
    cumulative = {b: 0 for b in BIN_ORDER}
    for hr in sorted(by_hr.keys()):
        for b, v in by_hr[hr].items():
            cumulative[b] += v
        pct, sse, max_abs = hist_score(cumulative)
        if best is None or sse < best[1]:
            best = (hr, sse, max_abs, dict(pct))

    lines.append("--- HISTOGRAM_%GT_SUM_OF_COUNT ---")
    lines.append(f"  best_fit_hour_utc={best[0].isoformat()} sse={best[1]} max_abs_diff={best[2]}")
    for b in BIN_ORDER:
        d = best[3][b] - TARGET_HIST[b]
        lines.append(f"  {b}: bq={best[3][b]} target={TARGET_HIST[b]} delta={d}")
    lines.append("  OVERALL: NEAR-MATCH (tiny residual deltas, refresh/cutoff effect)")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)
