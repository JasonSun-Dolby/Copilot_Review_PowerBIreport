from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_video_stripped_monthly_stats_result.txt")

q = """
WITH base AS (
  SELECT
    DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH) AS month,
    CAST(duration_sec AS FLOAT64) AS duration_sec,
    PERCENTILE_CONT(CAST(duration_sec AS FLOAT64), 0.5)
      OVER (PARTITION BY DATE_TRUNC(DATE(TIMESTAMP_MICROS(event_timestamp)), MONTH)) AS median_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.video_recording_events_stripped`
)
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  MAX(duration_sec) AS max_duration_sec,
  MAX(duration_sec) / 3600.0 AS max_duration_hour,
  AVG(duration_sec) AS mean_duration_sec,
  ANY_VALUE(median_duration_sec) AS median_duration_sec
FROM base
GROUP BY month
ORDER BY month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
lines = [str(dict(r.items())) for r in rows]
out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
print("wrote", out, "rows", len(rows))
