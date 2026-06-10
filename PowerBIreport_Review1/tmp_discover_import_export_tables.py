from google.cloud import bigquery
c = bigquery.Client(project="ap3-prod-0e613121")
q = (
    "SELECT table_name, table_type "
    "FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.TABLES "
    "WHERE LOWER(table_name) LIKE '%import%' "
    "   OR LOWER(table_name) LIKE '%export%' "
    "   OR LOWER(table_name) LIKE '%aggregar%' "
    "ORDER BY table_name"
)
rows = list(c.query(q).result())
print(f"Found {len(rows)} tables:")
for r in rows:
    print(f"  {r.table_name}  ({r.table_type})")
