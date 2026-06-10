from pathlib import Path
from google.cloud import bigquery

out = Path('tmp_query_india_2026_02_result.txt')
q = """
SELECT
  month,
  country,
  active_audio_users,
  active_video_users,
  active_livestream_users,
  total_active_users
FROM `ap3-prod-0e613121.analytics_184529778.monthly_country_active_users_aggregated`
WHERE month = DATE '2026-02-01' AND country = 'India'
"""

client = bigquery.Client(project='ap3-prod-0e613121')
rows = list(client.query(q).result())
out.write_text('\n'.join(str(dict(r.items())) for r in rows), encoding='ascii', errors='ignore')
print('rows', len(rows))
