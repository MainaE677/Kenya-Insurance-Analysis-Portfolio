"""
CIC General Insurance -- Q1 2025 vs Q1 2026 Performance Analysis
Source: Insurance Regulatory Authority (IRA) of Kenya, Quarterly Industry Statistics
https://www.ira.go.ke/quarterly-reports/

This script loads, cleans, and compares IRA's quarterly industry statistics
Excel releases, producing a clean set of CSVs used in the accompanying
Power BI dashboard.
"""

import pandas as pd
import os

RAW_DIR = "../data/raw"
OUT_DIR = "../data/processed"
os.makedirs(OUT_DIR, exist_ok=True)


def load_ira_sheet(file_path, sheet_name, quarter_label):
    """Load and clean a single sheet from an IRA quarterly statistics file."""
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=3)
    df = df.drop(columns=[df.columns[0]])                        # drop empty first column
    df = df[df["Company"] != "INSURERS"]                         # drop stray subheader row
    df = df.dropna(subset=["Company"])                           # drop blank rows
    df.columns = [str(c).replace("_x000D_\n", "").strip() for c in df.columns]
    df["quarter"] = quarter_label
    return df


# ============================================
# STEP 1: Load Q1 2026 (baseline file)
# ============================================
file_q1_2026 = os.path.join(RAW_DIR, "Quarter-1_2026__Industry_Statistics.xlsx")

gdp_q1_2026 = load_ira_sheet(file_q1_2026, "GDP", "Q1_2026")
npi_q1_2026 = load_ira_sheet(file_q1_2026, "NPI", "Q1_2026")
uwprofit_q1_2026 = load_ira_sheet(file_q1_2026, "UWProfit", "Q1_2026")
appendix18_q1_2026 = load_ira_sheet(file_q1_2026, "APPENDIX 18", "Q1_2026")

# --- Market share: split primary insurers vs reinsurers ---
appendix18_clean = appendix18_q1_2026[
    ~appendix18_q1_2026["Company"].str.contains("TOTAL", na=False)
]
is_reinsurer = appendix18_clean["Company"].str.contains("REINSURANCE|REINSURER", na=False)
primary_insurers = appendix18_clean[~is_reinsurer]
reinsurers = appendix18_clean[is_reinsurer].dropna(subset=["Total"])

print("Top 10 primary insurers by market share (Q1 2026):")
print(primary_insurers[["Company", "Total", "Market Share (%)"]]
      .sort_values("Market Share (%)", ascending=False).head(10))

# --- CIC scorecard ---
cic_summary = pd.DataFrame({
    "Metric": ["Gross Direct Premium", "Net Premium Income", "Underwriting Profit/Loss"],
    "Value": [
        gdp_q1_2026.loc[gdp_q1_2026["Company"].str.contains("CIC", na=False), "Total"].values[0],
        npi_q1_2026.loc[npi_q1_2026["Company"].str.contains("CIC", na=False), "Total"].values[0],
        uwprofit_q1_2026.loc[uwprofit_q1_2026["Company"].str.contains("CIC", na=False), "Total"].values[0],
    ]
})
print("\nCIC General -- Q1 2026 Scorecard:")
print(cic_summary)

# ============================================
# STEP 2: Load Q1 2025 (true Q1-to-Q1 comparison)
# ============================================
file_q1_2025 = os.path.join(RAW_DIR, "Quarter-1_2025__Industry_Statistics.xlsx")

gdp_q1_2025 = load_ira_sheet(file_q1_2025, "GDP", "Q1_2025")
uwprofit_q1_2025 = load_ira_sheet(file_q1_2025, "APPENDIX 20", "Q1_2025")  # renamed sheet in this release
npi_q1_2025 = load_ira_sheet(file_q1_2025, "NPI", "Q1_2025")

# --- CIC Q1-over-Q1 trend (clean, comparable periods) ---
gdp_qoq = pd.concat([gdp_q1_2025, gdp_q1_2026], ignore_index=True)
uw_qoq = pd.concat([uwprofit_q1_2025, uwprofit_q1_2026], ignore_index=True)

cic_gdp_trend = gdp_qoq.loc[gdp_qoq["Company"].str.contains("CIC", na=False), ["Company", "Total", "quarter"]]
cic_uw_trend = uw_qoq.loc[uw_qoq["Company"].str.contains("CIC", na=False), ["Company", "Total", "quarter"]]

print("\nCIC Gross Direct Premium -- Q1 2025 vs Q1 2026:")
print(cic_gdp_trend)
print("\nCIC Underwriting Profit/Loss -- Q1 2025 vs Q1 2026:")
print(cic_uw_trend)

# --- Market-wide Q1-over-Q1 growth ranking ---
gdp_merged = gdp_q1_2025[["Company", "Total"]].merge(
    gdp_q1_2026[["Company", "Total"]], on="Company", suffixes=("_Q1_2025", "_Q1_2026")
)
gdp_merged["GDP_Growth_%"] = (
    (gdp_merged["Total_Q1_2026"] - gdp_merged["Total_Q1_2025"])
    / gdp_merged["Total_Q1_2025"] * 100
).round(2)
gdp_merged = gdp_merged[~gdp_merged["Company"].str.contains("TOTAL", na=False)]
gdp_merged_clean = gdp_merged[gdp_merged["Total_Q1_2025"] > 0]  # drop 0-baseline / inf rows

uw_merged = uwprofit_q1_2025[["Company", "Total"]].merge(
    uwprofit_q1_2026[["Company", "Total"]], on="Company", suffixes=("_Q1_2025", "_Q1_2026")
)
uw_merged["UW_Change"] = uw_merged["Total_Q1_2026"] - uw_merged["Total_Q1_2025"]
uw_merged = uw_merged[~uw_merged["Company"].str.contains("TOTAL", na=False)]

print("\nTop 10 fastest-growing insurers by GDP (Q1 2025 -> Q1 2026, excluding 0-baseline rows):")
print(gdp_merged_clean.sort_values("GDP_Growth_%", ascending=False).head(10)
      [["Company", "Total_Q1_2025", "Total_Q1_2026", "GDP_Growth_%"]])

print("\nTop 10 insurers with worsening underwriting profit/loss:")
print(uw_merged.sort_values("UW_Change", ascending=True).head(10)
      [["Company", "Total_Q1_2025", "Total_Q1_2026", "UW_Change"]])

print("\nTop 10 insurers with improving underwriting profit/loss:")
print(uw_merged.sort_values("UW_Change", ascending=False).head(10)
      [["Company", "Total_Q1_2025", "Total_Q1_2026", "UW_Change"]])

# ============================================
# STEP 3: Load Full Year 2025 (cumulative -- kept SEPARATE from the QoQ trend)
# ============================================
# NOTE: The IRA file labelled "Quarter-4 2025" is in fact a cumulative
# Jan-Dec 2025 release, not a standalone Q4. Its title row confirms this:
# "...FOR THE PERIOD ENDED 31.12.2025". It is intentionally kept separate
# from the quarter-over-quarter trend above to avoid a misleading comparison.
file_fy_2025 = os.path.join(RAW_DIR, "Quarter-4_2025__Industry_Statistics.xlsx")

gdp_fy_2025 = load_ira_sheet(file_fy_2025, "GDP", "FY_2025_cumulative")
uwprofit_fy_2025 = load_ira_sheet(file_fy_2025, "UWProfit", "FY_2025_cumulative")

title_check = pd.read_excel(file_fy_2025, sheet_name="GDP", header=None, nrows=3).iloc[2, 1]
print(f"\nFull Year 2025 file period check: {title_check}")

print("\nCIC Full Year 2025 (cumulative -- NOT part of the Q1-Q1 quarterly trend):")
print(gdp_fy_2025.loc[gdp_fy_2025["Company"].str.contains("CIC", na=False), ["Company", "Total"]])
print(uwprofit_fy_2025.loc[uwprofit_fy_2025["Company"].str.contains("CIC", na=False), ["Company", "Total"]])

# ============================================
# STEP 4: Cleaned market-share export (TOTAL rows and reinsurers removed)
# ============================================
gdp_q1_2026_clean = gdp_q1_2026[~gdp_q1_2026["Company"].str.contains("TOTAL", na=False)]
gdp_q1_2026_clean = gdp_q1_2026_clean[
    ~gdp_q1_2026_clean["Company"].str.contains("REINSURANCE|REINSURER", na=False)
]

# ============================================
# STEP 5: Save clean outputs for Power BI
# ============================================
gdp_qoq.to_csv(os.path.join(OUT_DIR, "gdp_q1_trend.csv"), index=False)
uw_qoq.to_csv(os.path.join(OUT_DIR, "uwprofit_q1_trend.csv"), index=False)
gdp_fy_2025.to_csv(os.path.join(OUT_DIR, "gdp_fy2025_cumulative.csv"), index=False)
uwprofit_fy_2025.to_csv(os.path.join(OUT_DIR, "uwprofit_fy2025_cumulative.csv"), index=False)
gdp_q1_2026_clean.to_csv(os.path.join(OUT_DIR, "gdp_q1_2026_primary_insurers.csv"), index=False)

print("\nSaved cleaned CSVs to data/processed/")
