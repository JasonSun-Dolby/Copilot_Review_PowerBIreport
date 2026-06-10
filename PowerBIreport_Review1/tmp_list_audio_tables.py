from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_list_audio_tables_result.txt")
q = """
SELECT table_name
FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.TABLES
WHERE LOWER(table_name) LIKE '%audio%'
   OR LOWER(table_name) LIKE '%duration%'
   OR LOWER(table_name) LIKE '%hist%'
   OR LOWER(table_name) LIKE '%bin%'
ORDER BY table_name
"""

c = bigquery.Client(project="ap3-prod-0e613121")
rows = list(c.query(q).result())
out.write_text("\n".join(r.table_name for r in rows), encoding="ascii", errors="ignore")
print("wrote", out, "rows", len(rows))
