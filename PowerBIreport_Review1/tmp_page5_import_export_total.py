"""
Page 5 – 'Import and Export_Total'
Validation script: query monthly totals for audio/video imports and exports
and compare against Power BI visual values (fill in TARGET dicts once
you read the live page values).

Source tables (actual names resolved after running tmp_page5_discover_tables.py):
  monthly_audio_imports_aggregated / aggregared
  monthly_audio_exports_aggregated / aggregared
  monthly_video_imports_aggregated / aggregared
  monthly_video_exports_aggregated / aggregared
"""
from pathlib import Path
from google.cloud import bigquery

PROJECT = "ap3-prod-0e613121"
DATASET = "analytics_184529778"
out = Path("tmp_page5_import_export_total_result.txt")

# ── fill in live Power BI values once you read the page ──────────────────────
# TARGET_AUDIO_IMPORTS = { "2025-11": <value>, ... }
# TARGET_AUDIO_EXPORTS = { "2025-11": <value>, ... }
# TARGET_VIDEO_IMPORTS = { "2025-11": <value>, ... }
# TARGET_VIDEO_EXPORTS = { "2025-11": <value>, ... }
# ─────────────────────────────────────────────────────────────────────────────



def query_monthly_totals(client, table, date_col="month",
                          start="2025-11-01", end="2026-05-01"):
    """Return schema columns dynamically and query monthly aggregated values."""
    # First get column names
    schema_q = f"""
    SELECT column_name, data_type
    FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{table}'
    ORDER BY ordinal_position
    """
    cols = [(r.column_name, r.data_type) for r in client.query(schema_q).result()]
    numeric_cols = [c for c, t in cols if t in ("INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC")]
    agg_exprs = ", ".join(f"SUM({c}) AS {c}" for c in numeric_cols if c != date_col)

    q = f"""
    SELECT
      FORMAT_DATE('%Y-%m', {date_col}) AS month,
      {agg_exprs}
    FROM `{PROJECT}.{DATASET}.{table}`
    WHERE {date_col} BETWEEN DATE '{start}' AND DATE '{end}'
    GROUP BY 1
    ORDER BY 1
    """
    return list(client.query(q).result()), [c for c in numeric_cols if c != date_col]


def main():
    c = bigquery.Client(project=PROJECT)
    lines = []

    table_map = {
        "audio_imports": "monthly_audio_imports_aggregated",
        "audio_exports": "monthly_audio_exports_aggregated",
        "video_imports": "monthly_video_imports_aggregated",
        "video_exports": "monthly_video_exports_aggregated",
    }

    lines.append("=== RESOLVED TABLE NAMES ===")
    for label, tbl in table_map.items():
        lines.append(f"  {label}: {tbl}")

    for label, tbl in table_map.items():
        if tbl is None:
            lines.append(f"\n=== {label.upper()}: TABLE NOT FOUND ===")
            continue

        lines.append(f"\n=== {label.upper()} monthly totals ({tbl}) ===")
        try:
            rows, num_cols = query_monthly_totals(c, tbl)
            header = "  month  |  " + "  |  ".join(num_cols)
            lines.append(header)
            for r in rows:
                vals = "  |  ".join(
                    f"{r[col]:>18,.0f}" if r[col] is not None else "None"
                    for col in num_cols
                )
                lines.append(f"  {r.month}  |  {vals}")
        except Exception as e:
            lines.append(f"  ERROR: {e}")

    # Grand totals
    lines.append("\n=== GRAND TOTALS (all months) ===")
    for label, tbl in table_map.items():
        if tbl is None:
            continue
        schema_q = f"""
        SELECT column_name, data_type
        FROM `{PROJECT}.{DATASET}`.INFORMATION_SCHEMA.COLUMNS
        WHERE table_name = '{tbl}'
        ORDER BY ordinal_position
        """
        cols = [(r.column_name, r.data_type) for r in c.query(schema_q).result()]
        numeric_cols = [col for col, dt in cols if dt in ("INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC") and col != "month"]
        agg_exprs = ", ".join(f"SUM({col}) AS {col}" for col in numeric_cols)
        if not agg_exprs:
            continue
        tot_q = f"SELECT {agg_exprs} FROM `{PROJECT}.{DATASET}.{tbl}`"
        for r in c.query(tot_q).result():
            lines.append(f"  {label} ({tbl}):")
            for col in numeric_cols:
                lines.append(f"    {col}: {r[col]:,.0f}" if r[col] is not None else f"    {col}: None")

    out.write_text("\n".join(lines), encoding="ascii", errors="ignore")
    print("wrote", out)


if __name__ == "__main__":
    main()
