from pathlib import Path
from datetime import datetime, timezone

from google.cloud import bigquery

out = Path("tmp_optimize_hist_cutoff_both_sources_result.txt")

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


def query_for_table(table_name: str) -> str:
    return f"""
WITH b AS (
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
  FROM `ap3-prod-0e613121.analytics_184529778.{table_name}`
  GROUP BY hr, bin
)
SELECT hr, bin, cnt
FROM b
ORDER BY hr, bin
"""


def sse_for_counts(counts: dict[str, int]) -> tuple[float, float]:
    total = sum(counts.values())
    sse = 0.0
    max_abs = 0.0
    for b in TARGET_ORDER:
        pct = (counts.get(b, 0) / total) if total else 0.0
        d = pct - TARGET[b]
        sse += d * d
        if abs(d) > max_abs:
            max_abs = abs(d)
    return sse, max_abs


def best_for_table(c: bigquery.Client, table_name: str):
    rows = list(c.query(query_for_table(table_name)).result())

    by_hr: dict[datetime, dict[str, int]] = {}
    for r in rows:
        hr = r.hr.replace(tzinfo=timezone.utc)
        by_hr.setdefault(hr, {})[r.bin] = int(r.cnt)

    hours = sorted(by_hr.keys())
    cumulative = {b: 0 for b in TARGET_ORDER}
    best = None

    for hr in hours:
        for b, v in by_hr[hr].items():
            cumulative[b] += v
        sse, max_abs = sse_for_counts(cumulative)
        if best is None or sse < best[0]:
            best = (sse, max_abs, hr)

    return best


def main() -> None:
    c = bigquery.Client(project="ap3-prod-0e613121")
    lines = []

    for table in ["audio_recording_events_stripped", "audio_duration_view"]:
        best = best_for_table(c, table)
        lines.append(
            f"table={table}\tbest_sse={best[0]}\tbest_max_abs={best[1]}\tbest_hour={best[2].isoformat()}"
        )

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
