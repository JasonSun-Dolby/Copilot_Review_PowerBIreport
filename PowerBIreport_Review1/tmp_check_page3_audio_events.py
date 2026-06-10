from pathlib import Path

from google.cloud import bigquery

OUTPUT_PATH = Path("tmp_check_page3_audio_events_result.txt")

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"
TABLE = "audio_recording_events_stripped"

SCHEMA_QUERY = f"""
SELECT column_name, data_type
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = '{TABLE}'
ORDER BY ordinal_position
"""

MAX_BY_MONTH_QUERY = f"""
SELECT
  DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
  MAX(CAST(duration_sec AS FLOAT64) / 3600.0) AS max_duration_hour
FROM `{PROJECT}.{DATASET}.{TABLE}`
GROUP BY 1
ORDER BY month
"""

HIST_QUERY = f"""
WITH base AS (
  SELECT CAST(duration_sec AS FLOAT64) AS duration_sec
  FROM `{PROJECT}.{DATASET}.{TABLE}`
),
bins AS (
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
  FROM base
  GROUP BY bin
),
tot AS (
  SELECT SUM(cnt) AS total_cnt FROM bins
)
SELECT
  bin,
  cnt,
  SAFE_DIVIDE(cnt, total_cnt) AS pct
FROM bins, tot
ORDER BY CASE bin
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
    client = bigquery.Client(project=PROJECT)
    lines = []

    lines.append("===SCHEMA===")
    for row in client.query(SCHEMA_QUERY).result():
        lines.append(f"{row.column_name}\t{row.data_type}")

    lines.append("===MAX_BY_MONTH===")
    try:
        for row in client.query(MAX_BY_MONTH_QUERY).result():
            lines.append(str(dict(row.items())))
    except Exception as exc:
        lines.append(f"ERROR\t{type(exc).__name__}\t{exc}")

    lines.append("===HISTOGRAM===")
    try:
        for row in client.query(HIST_QUERY).result():
            lines.append(str(dict(row.items())))
    except Exception as exc:
        lines.append(f"ERROR\t{type(exc).__name__}\t{exc}")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", OUTPUT_PATH)


if __name__ == "__main__":
    main()
