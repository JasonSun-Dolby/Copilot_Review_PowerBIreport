"""
Step 1 – Discover actual import/export/recording table names and schemas.
The datasource note spells them with 'aggregared' (typo). Actual names may
be 'aggregated'. This script tries all candidate spellings and prints
whatever it finds in INFORMATION_SCHEMA.
"""
from pathlib import Path
from google.cloud import bigquery

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"
out = Path("tmp_page5_discover_tables_result.txt")

CANDIDATES = [
    # audio
    "monthly_audio_imports_aggregated",
    "monthly_audio_imports_aggregared",
    "monthly_audio_exports_aggregated",
    "monthly_audio_exports_aggregared",
    # video
    "monthly_video_imports_aggregated",
    "monthly_video_imports_aggregared",
    "monthly_video_exports_aggregated",
    "monthly_video_exports_aggregared",
    # recording (singular, as in the datasource note)
    "monthly_audio_recording_aggregated",
    "monthly_audio_recording_aggregared",
    "monthly_video_recording_aggregated",
    "monthly_video_recording_aggregared",
    # recordings (plural, already confirmed in BigQuery)
    "monthly_audio_recordings_aggregated",
    "monthly_video_recordings_aggregated",
]

Q_FIND = f"""
SELECT table_name, table_type
FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.TABLES
WHERE LOWER(table_name) LIKE '%import%'
   OR LOWER(table_name) LIKE '%export%'
   OR LOWER(table_name) LIKE '%recording%'
ORDER BY table_name
"""

Q_SCHEMA = """
SELECT column_name, data_type, ordinal_position
FROM `{project}.{dataset}`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = '{table}'
ORDER BY ordinal_position
"""

Q_SAMPLE = """
SELECT *
FROM `{project}.{dataset}.{table}`
LIMIT 3
"""


def main():
    c = bigquery.Client(project=PROJECT)
    lines = []

    # 1. Find all matching tables
    lines.append("=== TABLES MATCHING import/export/recording ===")
    found_tables = []
    for row in c.query(Q_FIND).result():
        lines.append(f"  {row.table_name}  ({row.table_type})")
        found_tables.append(row.table_name)

    # 2. Schema for each found table
    for tbl in found_tables:
        lines.append(f"\n=== SCHEMA: {tbl} ===")
        q = Q_SCHEMA.format(project=PROJECT, dataset=DATASET, table=tbl)
        for r in c.query(q).result():
            lines.append(f"  {r.ordinal_position}. {r.column_name}  {r.data_type}")

    # 3. First 3 rows for each found table
    for tbl in found_tables:
        lines.append(f"\n=== SAMPLE (3 rows): {tbl} ===")
        try:
            q = Q_SAMPLE.format(project=PROJECT, dataset=DATASET, table=tbl)
            for r in c.query(q).result():
                lines.append("  " + str(dict(r.items())))
        except Exception as e:
            lines.append(f"  ERROR: {e}")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
