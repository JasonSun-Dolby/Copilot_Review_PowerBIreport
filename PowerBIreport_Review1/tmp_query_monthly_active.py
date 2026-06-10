from pathlib import Path

from google.cloud import bigquery

TABLE = "`ap3-prod-0e613121.analytics_184529778.monthly_country_active_users_aggregated`"
OUTPUT_PATH = Path("tmp_query_monthly_active_result.txt")


def main() -> None:
    client = bigquery.Client(project="ap3-prod-0e613121")

    schema_query = """
SELECT column_name, data_type
FROM `ap3-prod-0e613121.analytics_184529778`.INFORMATION_SCHEMA.COLUMNS
WHERE table_name = 'monthly_country_active_users_aggregated'
ORDER BY ordinal_position
"""

    value_query = f"""
SELECT
  month,
  SUM(active_audio_users) AS active_audio_users,
  SUM(active_video_users) AS active_video_users,
  SUM(active_livestream_users) AS active_livestream_users,
  SUM(total_active_users) AS total_active_users
FROM {TABLE}
WHERE CAST(month AS STRING) >= '2025-09'
GROUP BY month
ORDER BY month
"""

    lines = ["===SCHEMA==="]
    for row in client.query(schema_query).result():
        lines.append(f"{row.column_name}\t{row.data_type}")

    lines.append("===VALUES===")
    for row in client.query(value_query).result():
        lines.append(str(dict(row.items())))

    OUTPUT_PATH.write_text("\n".join(lines), encoding="ascii", errors="ignore")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUTPUT_PATH.write_text(f"ERROR\n{type(exc).__name__}\n{exc}\n", encoding="ascii", errors="ignore")
        raise
