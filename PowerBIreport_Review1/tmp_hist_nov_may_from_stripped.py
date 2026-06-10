from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_hist_nov_may_from_stripped_result.txt")
q = """
WITH base AS (
  SELECT CAST(duration_sec AS FLOAT64) AS duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.audio_recording_events_stripped`
  WHERE DATE(TIMESTAMP_MICROS(event_timestamp)) >= DATE '2025-11-01'
    AND DATE(TIMESTAMP_MICROS(event_timestamp)) < DATE '2026-06-01'
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
SELECT bin, cnt, SAFE_DIVIDE(cnt, total_cnt) AS pct
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

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
out.write_text("\n".join(str(dict(r.items())) for r in rows), encoding="ascii", errors="ignore")
print("wrote", out)
