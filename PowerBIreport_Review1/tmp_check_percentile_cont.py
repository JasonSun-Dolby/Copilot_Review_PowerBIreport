from google.cloud import bigquery

q = """
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec,
    PERCENTILE_CONT(median_duration_sec, 0.5) OVER (PARTITION BY month) AS p50_median_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  month,
  AVG(mean_duration_sec) AS Mean_duration_sec,
  ANY_VALUE(p50_median_sec) AS Median_duration_sec
FROM x
GROUP BY month
ORDER BY month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
for r in c.query(q).result():
    print(dict(r.items()))
