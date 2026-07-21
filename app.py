import streamlit as st
import pandas as pd
import numpy as np
import io

# ---------------------------------------------------------------------------------
# 🎨 EXECUTIVE ARCHITECTURE & GLOBAL PALETTE SETUP
# ---------------------------------------------------------------------------------
HEX_DEEP_BLUE = "#1652A3"
HEX_DARK_SLATE = "#3A414B"
HEX_LIGHT_BLUE = "#D5DEE7"
HEX_VIBRANT_BLUE = "#2F88F5"

# Currency follows the selected country: US = $, Canada = C$, Mexico = MX$.
# NOTE: Streamlit's markdown renderer treats a PAIR of literal "$" characters
# within the same plain-text call (st.caption/st.warning/st.markdown without
# unsafe_allow_html, st.write, expander labels) as LaTeX math-mode delimiters,
# silently dropping/mangling whatever sits between them. The raw currency_symbol
# is safe inside raw-HTML blocks (unsafe_allow_html=True), Styler.format()
# strings, and Plotly labels — none of those go through that markdown math
# parser. currency_symbol_md (backslash-escaped) is for plain-markdown text
# where two or more currency mentions might land in the same call.
CURRENCY_MAP = {
    "united states": {"symbol": "$", "code": "USD"},
    "us": {"symbol": "$", "code": "USD"},
    "usa": {"symbol": "$", "code": "USD"},
    "canada": {"symbol": "C$", "code": "CAD"},
    "ca": {"symbol": "C$", "code": "CAD"},
    "mexico": {"symbol": "MX$", "code": "MXN"},
    "mx": {"symbol": "MX$", "code": "MXN"},
}
DEFAULT_CURRENCY = {"symbol": "$", "code": ""}


def currency_for(country_name) -> dict:
    return CURRENCY_MAP.get(str(country_name).strip().lower(), DEFAULT_CURRENCY)


st.set_page_config(
    page_title="MerchantSpring | Advertising & Total Sales WBR Engine",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
    <style>
    .main {{ background-color: #FBFBFC; }}
    .kpi-card {{
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(58, 65, 75, 0.06);
        border-top: 5px solid {HEX_DEEP_BLUE};
        text-align: center;
    }}
    .kpi-card h4 {{ margin: 0 0 6px 0; color: #7f8c8d; font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; }}
    .kpi-card h2 {{ margin: 0; color: {HEX_DARK_SLATE}; font-size: 24px; font-weight: 800; }}
    .kpi-card p {{ margin: 4px 0 0 0; font-size: 12px; font-weight: 600; color: #566573; }}
    .strategic-banner {{
        background-color: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border-left: 6px solid {HEX_DEEP_BLUE};
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(58, 65, 75, 0.05);
    }}
    .insight-header {{
        font-size: 16px;
        font-weight: bold;
        color: {HEX_DARK_SLATE};
        margin-top: 15px;
        margin-bottom: 5px;
        border-bottom: 2px solid {HEX_LIGHT_BLUE};
        padding-bottom: 3px;
    }}
    .usecase-tag {{
        display: inline-block;
        background-color: {HEX_LIGHT_BLUE};
        color: {HEX_DARK_SLATE};
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 10px;
    }}
    </style>
""", unsafe_allow_html=True)

st.title("🦅 Sponsored Products Weekly Business Review (WBR) Console")
st.markdown("### Integrated Advertising Performance Funnels & Total Retail Sales Matrix")
st.markdown("---")

# ---------------------------------------------------------------------------------
# 📥 SIDEBAR CONTROL & DATAFRAME INGESTION
# ---------------------------------------------------------------------------------
st.sidebar.markdown(f"<h2 style='color: {HEX_DEEP_BLUE}; margin-top: 0;'>📥 Data Pipeline</h2>", unsafe_allow_html=True)
ad_file = st.sidebar.file_uploader("1️⃣ Upload Sponsored Product Ad Report", type=["csv", "xlsx"])
biz_file = st.sidebar.file_uploader("2️⃣ Upload Present Week Business Report (For TACoS)", type=["csv", "xlsx"])

if not ad_file:
    st.info("👋 **Console Parked:** Please upload your main advertising performance report in the sidebar to begin.")
    st.stop()

# Ingest Main Ad Report
try:
    if ad_file.name.endswith('.csv'):
        df_raw = pd.read_csv(ad_file)
    else:
        df_raw = pd.read_excel(ad_file)
except Exception as e:
    st.error(f"Error reading advertising file: {e}")
    st.stop()

df_raw.columns = df_raw.columns.str.strip()

# --- Layer 1: de-duplicate raw column labels BEFORE any mapping happens.
# pandas allows a DataFrame to have two columns with the identical label. If that
# happens, df_raw[c] on that label returns a DataFrame (not a Series) and anything
# downstream expecting Series behavior (e.g. .dtype) throws an AttributeError. This
# can happen even from the source file itself (merged headers, blank/repeated
# columns in an export), independent of our own renaming below.
if df_raw.columns.duplicated().any():
    dup_names = sorted(set(df_raw.columns[df_raw.columns.duplicated()].tolist()))
    st.sidebar.warning(
        f"⚠️ The uploaded file has duplicate column names — keeping only the first "
        f"occurrence of each: {', '.join(dup_names)}"
    )
    df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]

# --- Layer 2: claim-based column mapping. Amazon's report headers drift over time
# and across export paths, so the matching rules below are intentionally loose
# (substring matches like 'sales' in c_low). But a loose rule can match MORE THAN
# ONE source column (e.g. both "7 Day Total Sales" and "Ordered Product Sales"
# contain "sales"). Renaming both to "Sales" would recreate the exact duplicate-
# column problem Layer 1 just solved. So each canonical target name may only be
# claimed once, by the first matching source column — anything that would also
# match an already-claimed target keeps its original header instead of colliding.
col_mapping = {}
claimed_targets = set()
skipped_duplicates = []


def claim(col, target):
    if target in claimed_targets:
        skipped_duplicates.append((col, target))
        return
    col_mapping[col] = target
    claimed_targets.add(target)


for col in df_raw.columns:
    c_low = col.lower()
    if c_low == 'date' or ('date' in c_low and 'reporting' in c_low):
        claim(col, 'Date')
    elif 'portfolio' in c_low:
        claim(col, 'Portfolio Name')
    elif c_low == 'sku' or c_low == 'advertised sku':
        claim(col, 'SKU')
    elif c_low == 'campaign name':
        claim(col, 'Campaign Name')
    elif c_low == 'spend' and not any(x in c_low for x in ['acos', 'roas']):
        claim(col, 'Spend')
    elif ('sales' in c_low or 'revenue' in c_low) and not any(x in c_low for x in ['acos', 'roas', 'sku', 'other']):
        claim(col, 'Sales')
    elif c_low == 'clicks':
        claim(col, 'Clicks')
    elif c_low == 'impressions':
        claim(col, 'Impressions')
    elif 'country' in c_low or c_low == 'marketplace':
        claim(col, 'Country')

if skipped_duplicates:
    detail = "; ".join(f"'{col}' also looked like {target}" for col, target in skipped_duplicates)
    st.sidebar.info(
        f"ℹ️ Some columns matched a field that was already mapped, so they were left "
        f"under their original name rather than overwriting it: {detail}"
    )

df_raw = df_raw.rename(columns=col_mapping)

if 'Date' not in df_raw.columns:
    st.error("Missing valid 'Date' column in the uploaded ad report format.")
    st.stop()

df_raw['Date'] = pd.to_datetime(df_raw['Date'], errors='coerce')
df_raw = df_raw.dropna(subset=['Date'])

# --- Layer 3: defensive Series check. Even with Layers 1-2 in place, this keeps
# the numeric-cleanup loop from ever crashing the same way again if some other
# code path reintroduces a duplicate label in the future.
for c in ['Spend', 'Sales', 'Clicks', 'Impressions']:
    if c in df_raw.columns:
        col_data = df_raw[c]
        if isinstance(col_data, pd.DataFrame):
            col_data = col_data.iloc[:, 0]
        if col_data.dtype == object:
            col_data = col_data.astype(str).str.replace(r'[%\$,]', '', regex=True)
        df_raw[c] = pd.to_numeric(col_data, errors='coerce').fillna(0.0)
    else:
        df_raw[c] = 0.0

if 'Portfolio Name' not in df_raw.columns: df_raw['Portfolio Name'] = 'General Portfolio'
if 'SKU' not in df_raw.columns: df_raw['SKU'] = 'GEN-UNKNOWN'
if 'Campaign Name' not in df_raw.columns: df_raw['Campaign Name'] = 'Generic Campaign'

# ---------------------------------------------------------------------------------
# ⚙️ REFINED SEGMENTATION ROUTING FUNNEL
# ---------------------------------------------------------------------------------
# Each marketplace uses its own naming convention for the qualifying portfolio
# prefix: most countries (including Canada) use "FBA_", Mexico uses "NARF_".
# Vizari is excluded everywhere regardless of country or naming convention.
MEXICO_NAMES = {'mexico', 'mx'}


def required_prefix_for(country_str):
    return 'narf' if country_str in MEXICO_NAMES else 'fba'


def assign_wbr_portfolio(name, country=''):
    name_str = str(name).strip().lower()
    country_str = str(country).strip().lower()

    if 'viz' in name_str or 'vizari' in name_str:
        return 'EXCLUDE_FILTER'

    if required_prefix_for(country_str) not in name_str:
        return 'EXCLUDE_FILTER'

    # Isolate drop segments. MAP is intentionally NOT split out here — MAP-named
    # portfolios fall through to the 'fba' bucket below and are counted as part
    # of core FBA, unlike Exclusive/Ageing/CBT which remain their own segments.
    if 'exclusive' in name_str: return 'exclusive'
    elif 'ageing' in name_str: return 'ageing'
    elif 'cbt' in name_str: return 'cbt'
    else: return 'fba'


if 'Country' in df_raw.columns:
    df_raw['Mapped Portfolio'] = df_raw.apply(
        lambda r: assign_wbr_portfolio(r['Portfolio Name'], r['Country']), axis=1
    )
else:
    df_raw['Mapped Portfolio'] = df_raw['Portfolio Name'].apply(assign_wbr_portfolio)

# ---------------------------------------------------------------------------------
# 🌎 COUNTRY SELECTOR — single-select only. Portfolio qualifying rules (FBA vs
# NARF) and currency both differ by marketplace, so — unlike the earlier
# multi-country "All countries" option — only one country can be in view at a
# time. This runs BEFORE the included/excluded audit views are built below, so
# the portfolio list, KPIs, tables, and audit logs all reshuffle to show only
# what actually qualifies for the selected country, instead of a blended view.
# ---------------------------------------------------------------------------------
if 'Country' in df_raw.columns:
    country_options = sorted(df_raw['Country'].dropna().unique().tolist())
else:
    country_options = []

if country_options:
    default_country = 'United States' if 'United States' in country_options else country_options[0]
    st.sidebar.markdown("---")
    selected_country = st.sidebar.selectbox(
        "🌎 Country", country_options,
        index=country_options.index(default_country),
        help="One country at a time — portfolio qualifying rules (e.g. Mexico uses "
             "'NARF_' naming instead of 'FBA_') and currency both differ by "
             "marketplace, so mixing countries together isn't meaningful here.",
    )
    df_country_scoped = df_raw[df_raw['Country'] == selected_country]
else:
    selected_country = "N/A"
    df_country_scoped = df_raw

currency_symbol = currency_for(selected_country)["symbol"]
currency_code = currency_for(selected_country)["code"]
st.sidebar.caption(f"💱 Currency: {currency_code or currency_symbol} ({currency_symbol})")
currency_symbol_md = currency_symbol.replace("$", "\\$")

df_included_auditing = df_country_scoped[df_country_scoped['Mapped Portfolio'] != 'EXCLUDE_FILTER']
df_excluded_auditing = df_country_scoped[df_country_scoped['Mapped Portfolio'] == 'EXCLUDE_FILTER']

# Filter master processing dataset to valid mapped active FBA segments only
df_processed = df_included_auditing.copy()

if df_processed.empty:
    st.error(
        "No rows matched the routing rules for this country (portfolio name must "
        "contain 'fba' — or 'narf' for Mexico — and must not contain 'viz'/'vizari'). "
        "Check the 'Excluded Portfolios' log at the bottom of the page once data "
        "loads, or verify the Portfolio Name column in your file."
    )
    st.stop()


# 📅 TWO-PERIOD DATE SELECTION FUNNEL
# ---------------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Live Window Control")

# The original defaults hardcoded "last 7 days = P2, the 7 days before that = P1",
# which silently produces an INVALID range (P1 start after P1 end -> zero rows ->
# every "(Prev)"/"(Last Wk)" metric shows $0) whenever the uploaded file spans
# less than 14 days -- a very common case for a fresh weekly export. This now
# scales the split to whatever date range is actually present in the file.
data_min = df_processed['Date'].min()
data_max = df_processed['Date'].max()
total_days = (data_max - data_min).days + 1

if total_days >= 14:
    default_p2_start = data_max - pd.Timedelta(days=6)
    default_p2_end = data_max
    default_p1_start = data_min
    default_p1_end = default_p2_start - pd.Timedelta(days=1)
elif total_days >= 2:
    half = max(1, total_days // 2)
    default_p2_end = data_max
    default_p2_start = data_max - pd.Timedelta(days=half - 1)
    default_p1_end = default_p2_start - pd.Timedelta(days=1)
    default_p1_start = data_min
    st.sidebar.caption(
        f"File spans only {total_days} day(s), so P1/P2 default to a half-and-half "
        f"split instead of full weeks. Adjust the date pickers for a custom comparison."
    )
else:
    # Only a single day of data in the whole file -- mirror both periods rather
    # than producing an empty/invalid range.
    default_p1_start = default_p1_end = default_p2_start = default_p2_end = data_max
    st.sidebar.caption("File spans only 1 day, so P1 and P2 both show that same day.")

p1_start = st.sidebar.date_input("P1 Start Date", default_p1_start)
p1_end = st.sidebar.date_input("P1 End Date", default_p1_end)
p2_start = st.sidebar.date_input("P2 Start Date", default_p2_start)
p2_end = st.sidebar.date_input("P2 End Date", default_p2_end)

if p1_start > p1_end:
    st.sidebar.error("P1 Start Date is after P1 End Date — P1 metrics will show as zero until this is fixed.")
if p2_start > p2_end:
    st.sidebar.error("P2 Start Date is after P2 End Date — P2 metrics will show as zero until this is fixed.")

df_p1 = df_processed[(df_processed['Date'] >= pd.Timestamp(p1_start)) & (df_processed['Date'] <= pd.Timestamp(p1_end))].copy()
df_p2 = df_processed[(df_processed['Date'] >= pd.Timestamp(p2_start)) & (df_processed['Date'] <= pd.Timestamp(p2_end))].copy()

if df_p1.empty:
    st.sidebar.warning("No rows fall inside the P1 date range — all '(Prev)'/'(Last Wk)' columns will show $0.")
if df_p2.empty:
    st.sidebar.warning("No rows fall inside the P2 date range — all 'This Wk' metrics and the KPI cards will show $0.")

# Brand/vendor prefix identification. For most countries this is the first 4
# characters of the SKU (unchanged, original behavior). Canada and Mexico
# structure their portfolios by vendor instead: the text after "FBA_" (Canada)
# or "NARF_" (Mexico) in the Portfolio Name IS the brand/vendor name, so for
# those two countries the prefix is extracted from there instead — grouping by
# it below then naturally rolls up "all campaigns for that vendor" together.
CA_MARKER = 'fba_'
MX_MARKER = 'narf_'


def extract_marker_suffix(portfolio_name, marker):
    name = str(portfolio_name)
    idx = name.lower().find(marker)
    if idx == -1:
        return None
    remainder = name[idx + len(marker):].strip(' _-')
    return remainder.upper() if remainder else None


def compute_brand_prefix(row):
    country_str = str(row.get('Country', '')).strip().lower()
    portfolio_name = row.get('Portfolio Name', '')

    if country_str == 'canada' or country_str == 'ca':
        extracted = extract_marker_suffix(portfolio_name, CA_MARKER)
        if extracted:
            return extracted
    elif country_str in MEXICO_NAMES:
        extracted = extract_marker_suffix(portfolio_name, MX_MARKER)
        if extracted:
            return extracted

    return str(row.get('SKU', ''))[:4].upper()


if 'Country' in df_p1.columns:
    df_p1['Brand Prefix'] = df_p1.apply(compute_brand_prefix, axis=1)
else:
    df_p1['Brand Prefix'] = df_p1['SKU'].astype(str).str[:4].str.upper()

if 'Country' in df_p2.columns:
    df_p2['Brand Prefix'] = df_p2.apply(compute_brand_prefix, axis=1)
else:
    df_p2['Brand Prefix'] = df_p2['SKU'].astype(str).str[:4].str.upper()

# ---------------------------------------------------------------------------------
# ⚡️ SELLER CENTRAL BUSINESS REPORT PARSING ENGINE (PRESENT WEEK ONLY)
# ---------------------------------------------------------------------------------
biz_sales_p2 = 0.0
has_tacos_p2 = False

if biz_file:
    try:
        if biz_file.name.endswith('.csv'):
            df_b = pd.read_csv(biz_file)
        else:
            df_b = pd.read_excel(biz_file)

        if df_b.columns.duplicated().any():
            df_b = df_b.loc[:, ~df_b.columns.duplicated()]

        if len(df_b.columns) >= 21:
            sku_header = df_b.columns[3]
            sales_header = df_b.columns[20]
            
            df_b[sales_header] = df_b[sales_header].astype(str).str.replace(r'[%\$,]', '', regex=True)
            df_b['Parsed_Rev'] = pd.to_numeric(df_b[sales_header], errors='coerce').fillna(0.0)
            
            df_filtered = df_b[df_b[sku_header].astype(str).str.upper().str.contains('FBA|SNL', regex=True, na=False)]
            biz_sales_p2 = df_filtered['Parsed_Rev'].sum()
            if biz_sales_p2 > 0:
                has_tacos_p2 = True
        else:
            st.sidebar.warning(
                f"Business report has only {len(df_b.columns)} columns; expected at "
                f"least 21 to locate the SKU and Sales columns by position. TACoS will "
                f"show as N/A."
            )
    except Exception as e:
        st.sidebar.error(f"Error parsing business sheet: {e}")

# ---------------------------------------------------------------------------------
# 🧮 UNIFIED CORE FBA CALCULATIONS (EXCLUDES EXCLUSIVE, CBT, AGEING; MAP IS PART OF FBA)
# ---------------------------------------------------------------------------------
p2_core_fba = df_p2[df_p2['Mapped Portfolio'] == 'fba']
t_sp_core = p2_core_fba['Spend'].sum()
t_sl_core = p2_core_fba['Sales'].sum()

t_ac_core = (t_sp_core / t_sl_core * 100) if t_sl_core > 0 else 0.0
unique_brands = p2_core_fba['Brand Prefix'].nunique()

# KPI Header Cards Ribbon (Now representing Core FBA strictly)
st.caption(
    f"🌎 {selected_country} · Comparing {p1_start} → {p1_end} (Prev) vs {p2_start} → {p2_end} (This Wk)"
)
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
with col_kpi1: 
    st.markdown(f"<div class='kpi-card'><h4>Active Brands</h4><h2>{unique_brands}</h2><p>Core FBA SKU Prefixes</p></div>", unsafe_allow_html=True)
with col_kpi2: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: {HEX_VIBRANT_BLUE};'><h4>Core FBA Spend</h4><h2>{currency_symbol}{t_sp_core:,.2f}</h2><p>Excludes Excl/CBT/Ageing</p></div>", unsafe_allow_html=True)
with col_kpi3: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: #2ECC71;'><h4>Core FBA Sales</h4><h2>{currency_symbol}{t_sl_core:,.2f}</h2><p>Core Attributed Rev</p></div>", unsafe_allow_html=True)
with col_kpi4: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: #E67E22;'><h4>Core Blended ACoS</h4><h2>{t_ac_core:.2f}%</h2><p>Total Core Spends / Sales</p></div>", unsafe_allow_html=True)
with col_kpi5:
    if has_tacos_p2:
        st.markdown(f"<div class='kpi-card' style='border-top-color: #9B59B6;'><h4>Core Blended TACoS</h4><h2>{(t_sp_core / biz_sales_p2 * 100):.2f}%</h2><p>Core Spend / Total Shipped Sales</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='kpi-card' style='border-top-color: #CCD1D1;'><h4>Core Blended TACoS</h4><h2>N/A</h2><p>Upload Present Week Biz Report</p></div>", unsafe_allow_html=True)

st.markdown("---")

# Helper for table visual conditioning matrix
def style_comparison_matrix(df):
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    for idx in df.index:
        # Spend Side-by-Side Highlights
        if 'Spend (Last Wk)' in df.columns and 'Spend (This Wk)' in df.columns:
            if df.loc[idx, 'Spend (Last Wk)'] > df.loc[idx, 'Spend (This Wk)']:
                style_df.loc[idx, 'Spend (Last Wk)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #D4EFDF'
            elif df.loc[idx, 'Spend (Last Wk)'] < df.loc[idx, 'Spend (This Wk)']:
                style_df.loc[idx, 'Spend (Last Wk)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #FADBD8'
        
        # Sales Side-by-Side Highlights
        if 'Sales (Last Wk)' in df.columns and 'Sales (This Wk)' in df.columns:
            if df.loc[idx, 'Sales (Last Wk)'] > df.loc[idx, 'Sales (This Wk)']:
                style_df.loc[idx, 'Sales (Last Wk)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #FADBD8'
            elif df.loc[idx, 'Sales (Last Wk)'] < df.loc[idx, 'Sales (This Wk)']:
                style_df.loc[idx, 'Sales (Last Wk)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #D4EFDF'
        
        # ACoS Side-by-Side Highlights
        if 'ACoS (Last Wk)' in df.columns and 'ACoS (This Wk)' in df.columns:
            if df.loc[idx, 'ACoS (Last Wk)'] > df.loc[idx, 'ACoS (This Wk)']:
                style_df.loc[idx, 'ACoS (Last Wk)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'ACoS (This Wk)'] = 'background-color: #D4EFDF'
            elif df.loc[idx, 'ACoS (Last Wk)'] < df.loc[idx, 'ACoS (This Wk)']:
                style_df.loc[idx, 'ACoS (Last Wk)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'ACoS (This Wk)'] = 'background-color: #FADBD8'

        # Retain support for standard portfolio naming layout metrics
        if 'Spend (Prev)' in df.columns and 'Spend (This Wk)' in df.columns:
            if df.loc[idx, 'Spend (Prev)'] > df.loc[idx, 'Spend (This Wk)']:
                style_df.loc[idx, 'Spend (Prev)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #D4EFDF'
            elif df.loc[idx, 'Spend (Prev)'] < df.loc[idx, 'Spend (This Wk)']:
                style_df.loc[idx, 'Spend (Prev)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #FADBD8'
        if 'Sales (Prev)' in df.columns and 'Sales (This Wk)' in df.columns:
            if df.loc[idx, 'Sales (Prev)'] > df.loc[idx, 'Sales (This Wk)']:
                style_df.loc[idx, 'Sales (Prev)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #FADBD8'
            elif df.loc[idx, 'Sales (Prev)'] < df.loc[idx, 'Sales (This Wk)']:
                style_df.loc[idx, 'Sales (Prev)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #D4EFDF'
        if 'ACoS % (Prev)' in df.columns and 'ACoS % (This Wk)' in df.columns:
            if df.loc[idx, 'ACoS % (Prev)'] > df.loc[idx, 'ACoS % (This Wk)']:
                style_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #FADBD8'; style_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #D4EFDF'
            elif df.loc[idx, 'ACoS % (Prev)'] < df.loc[idx, 'ACoS % (This Wk)']:
                style_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #D4EFDF'; style_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #FADBD8'
    return style_df


tabs = st.tabs(["📋 Total FBA High-Level Summary", "📊 Portfolio Comparison Engine", "🏭 Vendor SKU Prefix Analytics", "💡 Deep-Dive Automated Insights"])

# ---------------------------------------------------------------------------------
# TAB 1: TOTAL FBA HIGH-LEVEL CHANNELS SUMMARY (Core FBA strictly matching the cards)
# ---------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("<span class='usecase-tag'>Total Business Channel Funnel</span>", unsafe_allow_html=True)
    st.markdown("<div class='strategic-banner'><b>FBA Summary Matrix:</b> Reflects present week metrics for standard FBA and MAP segments combined, while discarding Exclusive, CBT, and Ageing portfolios completely.</div>", unsafe_allow_html=True)
    
    high_level_data = {
        "Portfolio": ["FBA"],
        "Ad Sales": [f"{currency_symbol}{t_sl_core:,.2f}"],
        "Ad Spends": [f"{currency_symbol}{t_sp_core:,.2f}"],
        "ACoS": [f"{t_ac_core:.2f}%"],
        "TACoS": [f"{((t_sp_core / biz_sales_p2 * 100) if has_tacos_p2 else 0.0):.2f}%" if has_tacos_p2 else "N/A"]
    }
    st.dataframe(pd.DataFrame(high_level_data), use_container_width=True)

# ---------------------------------------------------------------------------------
# TAB 2: PORTFOLIO ENGINE
# ---------------------------------------------------------------------------------
with tabs[1]:
    p1_port = df_p1.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_port = df_p2.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    
    merged_port = pd.merge(p1_port, p2_port, on='Mapped Portfolio', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    merged_port['ACoS % (Prev)'] = np.where(merged_port['Sales (Prev)'] > 0, (merged_port['Spend (Prev)'] / merged_port['Sales (Prev)']) * 100, 0.0)
    merged_port['ACoS % (This Wk)'] = np.where(merged_port['Sales (This Wk)'] > 0, (merged_port['Spend (This Wk)'] / merged_port['Sales (This Wk)']) * 100, 0.0)
    
    order_cols = ['Mapped Portfolio', 'Spend (Prev)', 'Spend (This Wk)', 'Sales (Prev)', 'Sales (This Wk)', 'ACoS % (Prev)', 'ACoS % (This Wk)']
    final_port = merged_port.reindex(columns=order_cols).fillna(0.0)
    final_port = final_port.rename(columns={'Mapped Portfolio': 'Portfolio Segment'})
    
    st.dataframe(
        final_port.style.apply(style_comparison_matrix, axis=None).format({
            'Spend (Prev)': f'{currency_symbol}{{:,.2f}}', 'Spend (This Wk)': f'{currency_symbol}{{:,.2f}}',
            'Sales (Prev)': f'{currency_symbol}{{:,.2f}}', 'Sales (This Wk)': f'{currency_symbol}{{:,.2f}}',
            'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
        }),
        use_container_width=True
    )

# ---------------------------------------------------------------------------------
# TAB 3: VENDOR SKU PREFIX ANALYTICS (SIDE-BY-SIDE ORDER STRUCTURE)
# ---------------------------------------------------------------------------------
with tabs[2]:
    p1_brand = df_p1.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_brand = df_p2.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    
    merged_brand = pd.merge(p1_brand, p2_brand, on='Brand Prefix', how='outer', suffixes=(' (Last Wk)', ' (This Wk)')).fillna(0.0)
    merged_brand['ACoS (Last Wk)'] = np.where(merged_brand['Sales (Last Wk)'] > 0, (merged_brand['Spend (Last Wk)'] / merged_brand['Sales (Last Wk)']) * 100, 0.0)
    merged_brand['ACoS (This Wk)'] = np.where(merged_brand['Sales (This Wk)'] > 0, (merged_brand['Spend (This Wk)'] / merged_brand['Sales (This Wk)']) * 100, 0.0)
    
    # Restructure columns to establish side-by-side metric comparison blocks
    side_by_side_cols = [
        'Brand Prefix', 
        'Spend (Last Wk)', 'Spend (This Wk)', 
        'Sales (Last Wk)', 'Sales (This Wk)', 
        'ACoS (Last Wk)', 'ACoS (This Wk)'
    ]
    final_brand_sbs = merged_brand.reindex(columns=side_by_side_cols).fillna(0.0)
    top_20_sbs = final_brand_sbs.sort_values(by='Sales (This Wk)', ascending=False).head(20).reset_index(drop=True)
    
    st.markdown("<span class='usecase-tag'>Top 20 Brand Prefix SKU Matrix</span>", unsafe_allow_html=True)
    st.markdown(
        "<div class='strategic-banner'><b>Prefix Brand Intelligence:</b> Dynamic side-by-side metric "
        "layout comparison (Last Week vs This Week). Sorted by current high-revenue lines. For Canada, "
        "the prefix is the vendor name after <code>FBA_</code> in the portfolio; for Mexico, it's after "
        "<code>NARF_</code>. Every other country still uses the first 4 characters of the SKU.</div>",
        unsafe_allow_html=True,
    )
    
    st.dataframe(
        top_20_sbs.style.apply(style_comparison_matrix, axis=None).format({
            'Spend (Last Wk)': f'{currency_symbol}{{:,.2f}}', 'Spend (This Wk)': f'{currency_symbol}{{:,.2f}}',
            'Sales (Last Wk)': f'{currency_symbol}{{:,.2f}}', 'Sales (This Wk)': f'{currency_symbol}{{:,.2f}}',
            'ACoS (Last Wk)': '{:.2f}%', 'ACoS (This Wk)': '{:.2f}%'
        }),
        use_container_width=True
    )

# ---------------------------------------------------------------------------------
# TAB 4: AUTOMATED INSIGHTS GENERATION ENGINE
# ---------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("💡 Dynamic Operational Win & Failure Insights Engine")
    
    # 1. Portfolio Strategy Win Check
    best_port_row = final_port.sort_values(by='Sales (This Wk)', ascending=False).iloc[0] if not final_port.empty else None
    if best_port_row is not None:
        p_seg_name = best_port_row['Portfolio Segment']
        st.markdown(f"<div class='insight-header'>🟢 Portfolio Strategy Win: '{p_seg_name}' Segment Efficiency Optimized</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS decreased from {best_port_row['ACoS % (Prev)']:.2f}% to {best_port_row['ACoS % (This Wk)']:.2f}% as sales scaled to {currency_symbol}{best_port_row['Sales (This Wk)']:,.2f}.**")
        
        sub_camps = df_p2[df_p2['Mapped Portfolio'] == p_seg_name].groupby('Campaign Name').agg({'Sales':'sum', 'Spend':'sum'}).reset_index()
        top_camp_name = sub_camps.sort_values(by='Sales', ascending=False).iloc[0]['Campaign Name'] if not sub_camps.empty else "Core Placements"
        st.write(f"This performance lift is driven by clear structural conversion stability in the `{p_seg_name}` ad groups. Optimized keyword visibility and stable bid limits inside `{top_camp_name}` successfully scaled revenue without bloating customer acquisition thresholds, delivering reliable portfolio profitability.")

    # 2. Vendor Brand Prefix Strategy Win Check (Grossing >= $1000 and ACoS improved)
    # Re-map internally to matching side-by-side formats
    valid_wins = top_20_sbs[(top_20_sbs['Sales (This Wk)'] >= 1000.0) & (top_20_sbs['ACoS (This Wk)'] < top_20_sbs['ACoS (Last Wk)'])]
    if not valid_wins.empty:
        best_b_row = valid_wins.sort_values(by='Sales (This Wk)', ascending=False).iloc[0]
        b_pfx = best_b_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🟢 Vendor Brand Win: Prefix '{b_pfx}' Scales Profitable Volume</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS improved from {best_b_row['ACoS (Last Wk)']:.2f}% down to {best_b_row['ACoS (This Wk)']:.2f}% with total sales crossing {currency_symbol}{best_b_row['Sales (This Wk)']:,.2f}.**")
        st.write(f"The `{b_pfx}` vendor product catalog effectively hit scaling velocity by focusing on top-performing search term manual campaigns. Restricting lower-intent advertising leak areas minimized wasted spend, which improved target operating efficiency while protecting visibility on top revenue-driving listings.")

    # 3. Failures & Loss Corrections
    st.markdown("---")
    st.markdown("### ⚠️ System Failures & Loss Corrections")
    
    poor_port_row = final_port.sort_values(by='ACoS % (This Wk)', ascending=False).iloc[0] if not final_port.empty else None
    if poor_port_row is not None and poor_port_row['ACoS % (This Wk)'] > poor_port_row['ACoS % (Prev)']:
        p_seg_fail = poor_port_row['Portfolio Segment']
        st.markdown(f"<div class='insight-header'>🔴 Portfolio Margin Leak: `{p_seg_fail}` Segment Drift</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS expanded from {poor_port_row['ACoS % (Prev)']:.2f}% up to {poor_port_row['ACoS % (This Wk)']:.2f}%, indicating budget bleed.**")
        st.write(f"The efficiency loss in the `{p_seg_fail}` portfolio highlights a drop in conversion rates relative to overall click costs. Unoptimized automatic ad placements or broad match keywords have consumed too much budget without driving orders, requiring a quick review of negative targets and lower base bids.")

    valid_fails = top_20_sbs[(top_20_sbs['Sales (This Wk)'] >= 1000.0) & (top_20_sbs['ACoS (This Wk)'] > top_20_sbs['ACoS (Last Wk)'])]
    if not valid_fails.empty:
        poor_b_row = valid_fails.sort_values(by='ACoS (This Wk)', ascending=False).iloc[0]
        b_pfx_fail = poor_b_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🔴 Vendor Brand Failure: Prefix `{b_pfx_fail}` Over-Indexed Costs</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS deteriorated from {poor_b_row['ACoS (Last Wk)']:.2f}% up to {poor_b_row['ACoS (This Wk)']:.2f}% despite grossing {currency_symbol}{poor_b_row['Sales (This Wk)']:,.2f} in sales.**")
        st.write(f"While the `{b_pfx_fail}` inventory line maintains solid revenue volume, it is running into rising costs due to competitive bidding from other sellers. Higher click costs and lower page conversion rates mean an optimization sweep is needed to cut out low-converting search terms and protect net product margins.")

    # Master Workbook Export Engine
    master_buffer = io.BytesIO()
    with pd.ExcelWriter(master_buffer, engine='xlsxwriter') as writer:
        final_port.to_excel(writer, sheet_name='Portfolio Performance WBR', index=False)
        top_20_sbs.to_excel(writer, sheet_name='Vendor SKU WBR', index=False)
        
    st.download_button(
        label="📥 Export Complete Unified Master WBR Report to Excel",
        data=master_buffer.getvalue(),
        file_name="Master_WBR_Comparison_Unified.xlsx",
        mime="application/vnd.ms-excel"
    )

# ---------------------------------------------------------------------------------
# 🔍 GLOBAL LAYOUT FOOTER: PIPELINE AUDIT LOG DIRECTORIES (BELOW EVERY TAB)
# ---------------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Portfolio Pipeline Audit Logs")

with st.expander("👀 Click to Expand: Included FBA Portfolios & Campaigns"):
    st.markdown("**The following active FBA portfolios and campaigns are built directly into your KPI calculations and tabs above:**")
    if not df_included_auditing.empty:
        audit_inc = df_included_auditing.groupby(['Mapped Portfolio', 'Portfolio Name'])['Campaign Name'].unique().reset_index()
        for idx, row in audit_inc.iterrows():
            st.markdown(f"**📂 Segment:** `{row['Mapped Portfolio']}` | **Portfolio:** `{row['Portfolio Name']}` *({len(row['Campaign Name'])} campaigns)*")
            st.caption(", ".join(sorted(row['Campaign Name'])))
    else:
        st.warning("No active records matched your FBA routing rules.")
        
with st.expander("❌ Click to Expand: Excluded Portfolios & Campaigns (FBM / Vizari / Non-FBA)"):
    st.markdown("**The following items failed the FBA validation engine criteria and were automatically omitted from the dashboard tables:**")
    if not df_excluded_auditing.empty:
        audit_exc = df_excluded_auditing.groupby('Portfolio Name')['Campaign Name'].unique().reset_index()
        for idx, row in audit_exc.iterrows():
            st.markdown(f"**🗑️ Removed Portfolio:** `{row['Portfolio Name']}` *({len(row['Campaign Name'])} campaigns)*")
            st.caption(", ".join(sorted(row['Campaign Name'])))
    else:
        st.info("No records match standard exclusion criteria.")
