from google.cloud import bigquery
c = bigquery.Client(project="ap3-prod-0e613121")
q = (
    "SELECT table_name FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.TABLES "
    "WHERE LOWER(table_name) LIKE '%audio_recording%' "
    "   OR LOWER(table_name) LIKE '%video_recording%' "
    "ORDER BY table_name"
)
for r in c.query(q).result():
    print(r.table_name)
