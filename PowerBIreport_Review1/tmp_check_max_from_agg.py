from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_check_max_from_agg_result.txt")
q = """
SELECT
  month,
  MAX(max_duration_sec) / 3600.0 AS max_duration_hour
FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings_aggregated`
GROUP BY month
ORDER BY month
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
out.write_text("\n".join(str(dict(r.items())) for r in rows), encoding="ascii", errors="ignore")
print("wrote", out)
