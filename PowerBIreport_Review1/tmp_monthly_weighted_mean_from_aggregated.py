from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_monthly_weighted_mean_from_aggregated_result.txt")

q = """
WITH audio AS (
  SELECT
    FORMAT_DATE('%Y-%m', month) AS month,
    SUM(total_duration_sec) / SUM(num_tracks) AS mean_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
  GROUP BY 1
),
video AS (
  SELECT
    FORMAT_DATE('%Y-%m', month) AS month,
    SUM(total_duration_sec) / SUM(num_tracks) AS mean_duration_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
  GROUP BY 1
)
SELECT 'audio' AS source, month, mean_duration_sec
FROM audio
UNION ALL
SELECT 'video' AS source, month, mean_duration_sec
FROM video
ORDER BY source, month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
out.write_text("\n".join(str(dict(r.items())) for r in rows), encoding="ascii", errors="ignore")
print("wrote", out, "rows", len(rows))
