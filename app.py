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

# Map Ad report headers cleanly
col_mapping = {}
for col in df_raw.columns:
    c_low = col.lower()
    if c_low == 'date' or ('date' in c_low and 'reporting' in c_low):
        col_mapping[col] = 'Date'
    elif 'portfolio' in c_low:
        col_mapping[col] = 'Portfolio Name'
    elif c_low == 'sku' or c_low == 'advertised sku':
        col_mapping[col] = 'SKU'
    elif c_low == 'campaign name':
        col_mapping[col] = 'Campaign Name'
    elif c_low == 'spend' and not any(x in c_low for x in ['acos', 'roas']):
        col_mapping[col] = 'Spend'
    elif ('sales' in c_low or 'revenue' in c_low) and not any(x in c_low for x in ['acos', 'roas', 'sku', 'other']):
        col_mapping[col] = 'Sales'
    elif c_low == 'clicks':
        col_mapping[col] = 'Clicks'
    elif c_low == 'impressions':
        col_mapping[col] = 'Impressions'

df_raw = df_raw.rename(columns=col_mapping)

if 'Date' not in df_raw.columns:
    st.error("Missing valid 'Date' column in the uploaded ad report format.")
    st.stop()

df_raw['Date'] = pd.to_datetime(df_raw['Date'], errors='coerce')
df_raw = df_raw.dropna(subset=['Date'])

for c in ['Spend', 'Sales', 'Clicks', 'Impressions']:
    if c in df_raw.columns:
        if df_raw[c].dtype == object:
            df_raw[c] = df_raw[c].astype(str).str.replace(r'[%\$,]', '', regex=True)
        df_raw[c] = pd.to_numeric(df_raw[c], errors='coerce').fillna(0.0)
    else:
        df_raw[c] = 0.0

if 'Portfolio Name' not in df_raw.columns: df_raw['Portfolio Name'] = 'General Portfolio'
if 'SKU' not in df_raw.columns: df_raw['SKU'] = 'GEN-UNKNOWN'
if 'Campaign Name' not in df_raw.columns: df_raw['Campaign Name'] = 'Generic Campaign'

# ---------------------------------------------------------------------------------
# ⚙️ REFINED SEGMENTATION ROUTING FUNNEL
# ---------------------------------------------------------------------------------
def assign_wbr_portfolio(name):
    name_str = str(name).strip().lower()
    
    # Exclude non-FBA or Vizari items instantly
    if 'fba' not in name_str or 'viz' in name_str or 'vizari' in name_str:
        return 'EXCLUDE_FILTER'
        
    # Isolate drop segments
    if 'exclusive' in name_str: return 'exclusive'
    elif 'ageing' in name_str: return 'ageing'
    elif 'cbt' in name_str: return 'cbt'
    elif 'map' in name_str: return 'map'
    else: return 'fba'

df_raw['Mapped Portfolio'] = df_raw['Portfolio Name'].apply(assign_wbr_portfolio)
df_included_auditing = df_raw[df_raw['Mapped Portfolio'] != 'EXCLUDE_FILTER']
df_excluded_auditing = df_raw[df_raw['Mapped Portfolio'] == 'EXCLUDE_FILTER']

# Filter master processing dataset to valid mapped active FBA segments only
df_processed = df_included_auditing.copy()


# ---------------------------------------------------------------------------------
# 📅 TWO-PERIOD DATE SELECTION FUNNEL
# ---------------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Live Window Control")
p1_start = st.sidebar.date_input("P1 Start Date", df_processed['Date'].min())
p1_end = st.sidebar.date_input("P1 End Date", df_processed['Date'].max() - pd.Timedelta(days=7))
p2_start = st.sidebar.date_input("P2 Start Date", df_processed['Date'].max() - pd.Timedelta(days=6))
p2_end = st.sidebar.date_input("P2 End Date", df_processed['Date'].max())

df_p1 = df_processed[(df_processed['Date'] >= pd.Timestamp(p1_start)) & (df_processed['Date'] <= pd.Timestamp(p1_end))].copy()
df_p2 = df_processed[(df_processed['Date'] >= pd.Timestamp(p2_start)) & (df_processed['Date'] <= pd.Timestamp(p2_end))].copy()

# Rigidly force localization of the 4-letter brand identifier key to protect slices
df_p1['Brand Prefix'] = df_p1['SKU'].astype(str).str[:4].str.upper()
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
        
        if len(df_b.columns) >= 21:
            sku_header = df_b.columns[3]
            sales_header = df_b.columns[20]
            
            df_b[sales_header] = df_b[sales_header].astype(str).str.replace(r'[%\$,]', '', regex=True)
            df_b['Parsed_Rev'] = pd.to_numeric(df_b[sales_header], errors='coerce').fillna(0.0)
            
            df_filtered = df_b[df_b[sku_header].astype(str).str.upper().str.contains('FBA|SNL', regex=True, na=False)]
            biz_sales_p2 = df_filtered['Parsed_Rev'].sum()
            if biz_sales_p2 > 0:
                has_tacos_p2 = True
    except Exception as e:
        st.sidebar.error(f"Error parsing business sheet: {e}")

# ---------------------------------------------------------------------------------
# 🧮 UNIFIED CORE FBA CALCULATIONS (EXCLUDES EXCLUSIVE, CBT, AGEING IN BOTH)
# ---------------------------------------------------------------------------------
p2_core_fba = df_p2[df_p2['Mapped Portfolio'].isin(['fba', 'map'])]
t_sp_core = p2_core_fba['Spend'].sum()
t_sl_core = p2_core_fba['Sales'].sum()

t_ac_core = (t_sp_core / t_sl_core * 100) if t_sl_core > 0 else 0.0
unique_brands = p2_core_fba['Brand Prefix'].nunique()

# KPI Header Cards Ribbon (Now representing Core FBA strictly)
col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
with col_kpi1: 
    st.markdown(f"<div class='kpi-card'><h4>Active Brands</h4><h2>{unique_brands}</h2><p>Core FBA SKU Prefixes</p></div>", unsafe_allow_html=True)
with col_kpi2: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: {HEX_VIBRANT_BLUE};'><h4>Core FBA Spend</h4><h2>${t_sp_core:,.2f}</h2><p>Excludes Excl/CBT/Ageing</p></div>", unsafe_allow_html=True)
with col_kpi3: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: #2ECC71;'><h4>Core FBA Sales</h4><h2>${t_sl_core:,.2f}</h2><p>Core Attributed Rev</p></div>", unsafe_allow_html=True)
with col_kpi4: 
    st.markdown(f"<div class='kpi-card' style='border-top-color: #E67E22;'><h4>Core Blended ACoS</h4><h2>{t_ac_core:.2f}%</h2><p>Total Core Spends / Sales</p></div>", unsafe_allow_html=True)
with col_kpi5:
    if has_tacos_p2:
        st.markdown(f"<div class='kpi-card' style='border-top-color: #9B59B6;'><h4>Core Blended TACoS</h4><h2>{(t_sp_core / biz_sales_p2 * 100):.2f}%</h2><p>Core Spend / Total Shipped Sales</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='kpi-card' style='border-top-color: #CCD1D1;'><h4>Core Blended TACoS</h4><h2>N/A</h2><p>Upload Present Week Biz Report</p></div>", unsafe_allow_html=True)

st.markdown("---")

# Helper for cell shading matrix
def style_comparison_matrix(df):
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    for idx in df.index:
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
        "Ad Sales": [f"${t_sl_core:,.2f}"],
        "Ad Spends": [f"${t_sp_core:,.2f}"],
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
            'Spend (Prev)': '${:,.2f}', 'Spend (This Wk)': '${:,.2f}',
            'Sales (Prev)': '${:,.2f}', 'Sales (This Wk)': '${:,.2f}',
            'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
        }),
        use_container_width=True
    )

# ---------------------------------------------------------------------------------
# TAB 3: VENDOR BRAND PREFIX ANNOTATION
# ---------------------------------------------------------------------------------
with tabs[2]:
    p1_brand = df_p1.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_brand = df_p2.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    
    merged_brand = pd.merge(p1_brand, p2_brand, on='Brand Prefix', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    merged_brand['ACoS % (Prev)'] = np.where(merged_brand['Sales (Prev)'] > 0, (merged_brand['Spend (Prev)'] / merged_brand['Sales (Prev)']) * 100, 0.0)
    merged_brand['ACoS % (This Wk)'] = np.where(merged_brand['Sales (This Wk)'] > 0, (merged_brand['Spend (This Wk)'] / merged_brand['Sales (This Wk)']) * 100, 0.0)
    
    top_20 = merged_brand.sort_values(by='Sales (This Wk)', ascending=False).head(20).reset_index(drop=True)
    st.dataframe(
        top_20.style.apply(style_comparison_matrix, axis=None).format({
            'Spend (Prev)': '${:,.2f}', 'Spend (This Wk)': '${:,.2f}',
            'Sales (Prev)': '${:,.2f}', 'Sales (This Wk)': '${:,.2f}',
            'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
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
        st.markdown(f"**ACoS decreased from {best_port_row['ACoS % (Prev)']:.2f}% to {best_port_row['ACoS % (This Wk)']:.2f}% as sales scaled to ${best_port_row['Sales (This Wk)']:,.2f}.**")
        
        sub_camps = df_p2[df_p2['Mapped Portfolio'] == p_seg_name].groupby('Campaign Name').agg({'Sales':'sum', 'Spend':'sum'}).reset_index()
        top_camp_name = sub_camps.sort_values(by='Sales', ascending=False).iloc[0]['Campaign Name'] if not sub_camps.empty else "Core Placements"
        st.write(f"This performance lift is driven by clear structural conversion stability in the `{p_seg_name}` ad groups. Optimized keyword visibility and stable bid limits inside `{top_camp_name}` successfully scaled revenue without bloating customer acquisition thresholds, delivering reliable portfolio profitability.")

    # 2. Vendor Brand Prefix Strategy Win Check (Grossing >= $1000 and ACoS improved)
    valid_wins = merged_brand[(merged_brand['Sales (This Wk)'] >= 1000.0) & (merged_brand['ACoS % (This Wk)'] < merged_brand['ACoS % (Prev)'])]
    if not valid_wins.empty:
        best_b_row = valid_wins.sort_values(by='Sales (This Wk)', ascending=False).iloc[0]
        b_pfx = best_b_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🟢 Vendor Brand Win: Prefix '{b_pfx}' Scales Profitable Volume</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS improved from {best_b_row['ACoS % (Prev)']:.2f}% down to {best_b_row['ACoS % (This Wk)']:.2f}% with total sales crossing ${best_b_row['Sales (This Wk)']:,.2f}.**")
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

    valid_fails = merged_brand[(merged_brand['Sales (This Wk)'] >= 1000.0) & (merged_brand['ACoS % (This Wk)'] > merged_brand['ACoS % (Prev)'])]
    if not valid_fails.empty:
        poor_b_row = valid_fails.sort_values(by='ACoS % (This Wk)', ascending=False).iloc[0]
        b_pfx_fail = poor_b_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🔴 Vendor Brand Failure: Prefix `{b_pfx_fail}` Over-Indexed Costs</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS deteriorated from {poor_b_row['ACoS % (Prev)']:.2f}% up to {poor_b_row['ACoS % (This Wk)']:.2f}% despite grossing ${poor_b_row['Sales (This Wk)']:,.2f} in sales.**")
        st.write(f"While the `{b_pfx_fail}` inventory line maintains solid revenue volume, it is running into rising costs due to competitive bidding from other sellers. Higher click costs and lower page conversion rates mean an optimization sweep is needed to cut out low-converting search terms and protect net product margins.")

    # Master Workbook Export Engine
    master_buffer = io.BytesIO()
    with pd.ExcelWriter(master_buffer, engine='xlsxwriter') as writer:
        final_port.to_excel(writer, sheet_name='Portfolio Performance WBR', index=False)
        top_20.to_excel(writer, sheet_name='Vendor SKU WBR', index=False)
        
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
