"""
Estimate median from histogram bin(B) data using linear interpolation.
bin(B) uses 6-second bins: 0-2s, 2-8s, 8-14s, 14-20s, 20-26s, 26-32s, 32-38s, 38-44s, 44-50s, 50-56s, 56-60s

Live data extracted directly from the Power BI report page.
"""

# ----- Video (Page 4) bin(B) data from live report -----
VIDEO_BINS = [
    ("0-2s",   0,  2,  37896),
    ("2-8s",   2,  8,  277523),
    ("8-14s",  8, 14,  239918),
    ("14-20s",14, 20,  190954),
    ("20-26s",20, 26,  161168),
    ("26-32s",26, 32,  140969),
    ("32-38s",32, 38,  125985),
    ("38-44s",38, 44,  112232),
    ("44-50s",44, 50,  101867),
    ("50-56s",50, 56,   94666),
    ("56-60s",56, 60,   59862),
]

# ----- Audio (Page 3) bin(B) data from live report -----
AUDIO_BINS = [
    ("0-2s",   0,  2,  527650),
    ("2-8s",   2,  8, 5043406),
    ("8-14s",  8, 14, 3364059),
    ("14-20s",14, 20, 2190308),
    ("20-26s",20, 26, 1648254),
    ("26-32s",26, 32, 1318596),
    ("32-38s",32, 38, 1083774),
    ("38-44s",38, 44,  900785),
    ("44-50s",44, 50,  760087),
    ("50-56s",50, 56,  660483),
    ("56-60s",56, 60,  391367),
]


def interpolated_median(bins):
    """
    Estimate median by linear interpolation within the bin where cumulative count reaches 50%.
    bins: list of (label, start_sec, end_sec, count)
    Returns estimated median in seconds.
    """
    total = sum(b[3] for b in bins)
    half = total / 2.0
    cumulative = 0
    for label, start, end, cnt in bins:
        cumulative += cnt
        if cumulative >= half:
            # Proportion of this bin needed to reach the median
            prev_cumulative = cumulative - cnt
            fraction = (half - prev_cumulative) / cnt
            estimated_median = start + fraction * (end - start)
            return estimated_median, label, cnt, cumulative, total
    return None


def print_result(name, bins):
    total = sum(b[3] for b in bins)
    print(f"\n{'='*50}")
    print(f"  {name}  (total records: {total:,})")
    print(f"{'='*50}")
    print(f"  {'Bin':<10} {'Count':>10} {'Cumul':>12} {'Cumul%':>8}")
    print(f"  {'-'*44}")
    cumulative = 0
    half = total / 2.0
    for label, start, end, cnt in bins:
        cumulative += cnt
        pct = cumulative / total * 100
        marker = " <-- 50th pct" if cumulative >= half and (cumulative - cnt) < half else ""
        print(f"  {label:<10} {cnt:>10,} {cumulative:>12,} {pct:>7.2f}%{marker}")

    result = interpolated_median(bins)
    if result:
        med, bin_label, bin_cnt, bin_cumul, total = result
        print(f"\n  Median bin : {bin_label}")
        print(f"  Interpolated median = {med:.4f} seconds  ({med/60:.4f} minutes)")


print_result("VIDEO recordings (from bin(B) histogram)", VIDEO_BINS)
print_result("AUDIO recordings (from bin(B) histogram)", AUDIO_BINS)

print("""
Notes:
  - Exact BigQuery median (video, all months): ~38.7–40.8 sec (PERCENTILE_CONT from aggregated table)
  - Exact BigQuery median (audio, Nov-May):    ~22.1–24.6 sec (PERCENTILE_CONT from stripped table)
  - Histogram bin(B) median is an interpolation estimate across ALL months combined.
""")
