from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_page4_expected_mean_median_result.txt")
q = """
WITH x AS (
  SELECT
    month,
    mean_duration_sec,
    median_duration_sec,
    num_tracks,
    total_duration_sec,
    PERCENTILE_CONT(median_duration_sec, 0.5) OVER (PARTITION BY month) AS p50_median_sec
  FROM `ap3-prod-0e613121.analytics_184529778.monthly_video_recordings_aggregated`
  WHERE month BETWEEN DATE '2025-11-01' AND DATE '2026-05-01'
)
SELECT
  FORMAT_DATE('%Y-%m', month) AS month,
  AVG(mean_duration_sec) AS mean_duration_sec_avg,
  SUM(total_duration_sec) / SUM(num_tracks) AS mean_duration_sec_weighted,
  ANY_VALUE(p50_median_sec) AS median_duration_sec_p50
FROM x
GROUP BY month
ORDER BY month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
out.write_text("\n".join(str(dict(r.items())) for r in rows), encoding="ascii", errors="ignore")
print("wrote", out)
