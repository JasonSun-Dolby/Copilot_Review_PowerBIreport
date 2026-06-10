from pathlib import Path
from datetime import datetime, timezone

from google.cloud import bigquery

out = Path("tmp_optimize_hist_cutoff_second_result.txt")

TARGET_ORDER = [
    "0-1m",
    "1-5m",
    "5-10m",
    "10-15m",
    "15-20m",
    "20-25m",
    "25-30m",
    "0.5-1h",
    "1-8h",
    "8-24h",
    ">24h",
]
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

BASE_QUERY = """
WITH b AS (
  SELECT
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
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-29 20:00:00+00'
  GROUP BY bin
)
SELECT bin, cnt FROM b
"""

WINDOW_QUERY = """
WITH b AS (
  SELECT
    TIMESTAMP_TRUNC(TIMESTAMP_MICROS(event_timestamp), SECOND) AS ts,
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
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE TIMESTAMP_MICROS(event_timestamp) >= TIMESTAMP '2026-05-29 20:00:00+00'
    AND TIMESTAMP_MICROS(event_timestamp) < TIMESTAMP '2026-05-29 21:00:00+00'
  GROUP BY ts, bin
)
SELECT ts, bin, cnt
FROM b
ORDER BY ts, bin
"""


def score(counts: dict[str, int]) -> tuple[float, float]:
    total = sum(counts.values())
    sse = 0.0
    max_abs = 0.0
    for b in TARGET_ORDER:
        pct = counts.get(b, 0) / total
        d = pct - TARGET[b]
        sse += d * d
        if abs(d) > max_abs:
            max_abs = abs(d)
    return sse, max_abs


def main() -> None:
    c = bigquery.Client(project="ap3-prod-0e613121")

    base_rows = list(c.query(BASE_QUERY).result())
    win_rows = list(c.query(WINDOW_QUERY).result())

    counts = {b: 0 for b in TARGET_ORDER}
    for r in base_rows:
        counts[r.bin] = int(r.cnt)

    by_ts: dict[datetime, dict[str, int]] = {}
    for r in win_rows:
        ts = r.ts.replace(tzinfo=timezone.utc)
        by_ts.setdefault(ts, {})[r.bin] = int(r.cnt)

    best = (None, None, None)  # sse, max_abs, ts
    for ts in sorted(by_ts.keys()):
        for b, v in by_ts[ts].items():
            counts[b] += v
        sse, max_abs = score(counts)
        if best[0] is None or sse < best[0]:
            best = (sse, max_abs, ts)

    lines = [
        f"best_sse\t{best[0]}",
        f"best_max_abs\t{best[1]}",
        f"best_second_utc\t{best[2].isoformat()}",
    ]

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
