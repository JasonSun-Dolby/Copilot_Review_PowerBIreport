from pathlib import Path

from google.cloud import bigquery

out = Path("tmp_inspect_duration_sources_result.txt")

queries = {
    "schema_audio_duration_view": """
SELECT table_name, column_name, data_type
FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'audio_duration_view'
ORDER BY ordinal_position
""",
    "schema_monthly_audio_recordings": """
SELECT table_name, column_name, data_type
FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'monthly_audio_recordings'
ORDER BY ordinal_position
""",
    "sample_audio_duration_view": """
SELECT *
FROM `ap3-prod-0e613121.analytics_184529778.audio_duration_view`
LIMIT 10
""",
    "sample_monthly_audio_recordings": """
SELECT *
FROM `ap3-prod-0e613121.analytics_184529778.monthly_audio_recordings`
ORDER BY month, country
LIMIT 10
""",
}

c = bigquery.Client(project="ap3-prod-0e613121")
lines = []
for name, q in queries.items():
    lines.append(f"==={name}===")
    try:
        rows = list(c.query(q).result())
        for r in rows:
            lines.append(str(dict(r.items())))
    except Exception as exc:
        lines.append(f"ERROR\t{type(exc).__name__}\t{exc}")

out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
print("wrote", out)
