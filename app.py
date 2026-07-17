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
    page_title="MerchantSpring | Advertising WBR Engine",
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
st.markdown("### Multi-Period Performance Matrix & Cross-Brand Delta Comparison Engine")
st.markdown("---")


# ---------------------------------------------------------------------------------
# 📥 SIDEBAR CONTROL & DATAFRAME INGESTION
# ---------------------------------------------------------------------------------
st.sidebar.markdown(f"<h2 style='color: {HEX_DEEP_BLUE}; margin-top: 0;'>📥 Data Pipeline</h2>", unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("Upload Sponsored Product Advertising Report", type=["csv", "xlsx"])

if not uploaded_file:
    st.info("👋 **Console Parked:** Please upload an advertising performance report (CSV/XLSX) to initialize the WBR matrix data model.")
    st.stop()

# Load file dynamically based on file format
try:
    if uploaded_file.name.endswith('.csv'):
        df_raw = pd.read_csv(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Error parsing file: {e}. Please ensure it is a clean marketplace export.")
    st.stop()

# Standardize and clean trailing/leading whitespaces from headers
df_raw.columns = df_raw.columns.str.strip()

# ---------------------------------------------------------------------------------
# ⚡️ RIGOROUS, NON-OVERLAPPING COLUMN MAPPING ENGINE
# ---------------------------------------------------------------------------------
col_mapping = {}
for col in df_raw.columns:
    c_low = col.lower()
    
    # 1. Date column mapping
    if c_low == 'date' or ( 'date' in c_low and 'reporting' in c_low ):
        col_mapping[col] = 'Date'
        
    # 2. Portfolio Name mapping
    elif 'portfolio' in c_low:
        col_mapping[col] = 'Portfolio Name'
        
    # 3. Main Advertised SKU mapping
    elif c_low == 'sku' or c_low == 'advertised sku':
        col_mapping[col] = 'SKU'
        
    # 4. Strict Ad Spend column mapping
    elif c_low == 'spend' and not any(x in c_low for x in ['acos', 'roas']):
        col_mapping[col] = 'Spend'
        
    # 5. Strict Total Sales mapping
    elif ('sales' in c_low or 'revenue' in c_low) and not any(x in c_low for x in ['acos', 'roas', 'sku', 'other']):
        col_mapping[col] = 'Sales'
        
    # 6. Click & Impression Funnel mapping for summary calculations
    elif c_low == 'clicks':
        col_mapping[col] = 'Clicks'
    elif c_low == 'impressions':
        col_mapping[col] = 'Impressions'

df_raw = df_raw.rename(columns=col_mapping)

if 'Date' not in df_raw.columns:
    st.error("Missing a valid 'Date' column in the uploaded report format.")
    st.stop()

df_raw['Date'] = pd.to_datetime(df_raw['Date'], errors='coerce')
df_raw = df_raw.dropna(subset=['Date'])

# Clean and transform numeric advertising inputs safely on unique Series
for num_col in ['Spend', 'Sales', 'Clicks', 'Impressions']:
    if num_col in df_raw.columns:
        if df_raw[num_col].dtype == object:
            df_raw[num_col] = df_raw[num_col].astype(str).str.replace(r'[%\$,]', '', regex=True)
        df_raw[num_col] = pd.to_numeric(df_raw[num_col], errors='coerce').fillna(0.0)
    else:
        df_raw[num_col] = 0.0

if 'Portfolio Name' not in df_raw.columns:
    df_raw['Portfolio Name'] = 'General Portfolio'
if 'SKU' not in df_raw.columns:
    df_raw['SKU'] = 'GEN-UNKNOWN'
if 'Campaign Name' not in df_raw.columns:
    df_raw['Campaign Name'] = 'Generic Campaign'


# ---------------------------------------------------------------------------------
# ⚙️ STRICT FBA-ONLY PORTFOLIO ROUTING ENGINE (WITH VIZARI EXCLUSIONS)
# ---------------------------------------------------------------------------------
def assign_wbr_portfolio(name):
    name_str = str(name).strip().lower()
    
    # Rule 1: Must have 'fba' in it to even proceed
    if 'fba' not in name_str:
        return 'EXCLUDE_FILTER'
        
    # Rule 2: Exclude if it has VIZ or VIZARI in it (even if it contains FBA)
    if 'viz' in name_str or 'vizari' in name_str:
        return 'EXCLUDE_FILTER'
        
    # Rule 3: Map the surviving FBA portfolios
    if 'map' in name_str:
        return 'map'
    elif 'ageing' in name_str:
        return 'ageing'
    elif 'exclusive' in name_str:
        return 'exclusive'
    else:
        return 'fba'

df_raw['Mapped Portfolio'] = df_raw['Portfolio Name'].apply(assign_wbr_portfolio)

# Capture references before dropping row records for auditing expansion below
df_included_auditing = df_raw[df_raw['Mapped Portfolio'] != 'EXCLUDE_FILTER']
df_excluded_auditing = df_raw[df_raw['Mapped Portfolio'] == 'EXCLUDE_FILTER']

# Filter master processing dataset to valid mapped active FBA segments only
df_processed = df_included_auditing.copy()


# ---------------------------------------------------------------------------------
# 📅 TWO-PERIOD DATE SELECTION FUNNEL
# ---------------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Period 1 Scope (Previous Week)")
p1_start = st.sidebar.date_input("P1 Start Date", df_processed['Date'].min())
p1_end = st.sidebar.date_input("P1 End Date", df_processed['Date'].max() - pd.Timedelta(days=7))

st.sidebar.markdown("### 📅 Period 2 Scope (This Week)")
p2_start = st.sidebar.date_input("P2 Start Date", df_processed['Date'].max() - pd.Timedelta(days=6))
p2_end = st.sidebar.date_input("P2 End Date", df_processed['Date'].max())

# Isolate periods
df_p1 = df_processed[(df_processed['Date'] >= pd.Timestamp(p1_start)) & (df_processed['Date'] <= pd.Timestamp(p1_end))]
df_p2 = df_processed[(df_processed['Date'] >= pd.Timestamp(p2_start)) & (df_processed['Date'] <= pd.Timestamp(p2_end))]


# ---------------------------------------------------------------------------------
# 👑 EXECUTIVE SUMMARY RIBBON: BLENDED FBA PERFORMANCE MATRIX
# ---------------------------------------------------------------------------------
df_active_window = df_p2 if not df_p2.empty else df_processed
df_active_window = df_active_window.copy()
df_active_window['Derived Brand'] = df_active_window['SKU'].astype(str).str[:4].str.upper()

# Compute aggregates for active FBA pipeline
tot_spend = df_active_window['Spend'].sum()
tot_sales = df_active_window['Sales'].sum()
tot_clicks = df_active_window['Clicks'].sum()
tot_impr = df_active_window['Impressions'].sum()

global_acos = (tot_spend / tot_sales * 100) if tot_sales > 0 else 0.0
global_ctr = (tot_clicks / tot_impr * 100) if tot_impr > 0 else 0.0
global_cpc = (tot_spend / tot_clicks) if tot_clicks > 0 else 0.0
unique_brands = df_active_window['Derived Brand'].nunique()

col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
with col_kpi1:
    st.markdown(f"""<div class='kpi-card'>
        <h4>Active Brands</h4>
        <h2>{unique_brands}</h2>
        <p>FBA SKU Prefixes</p>
    </div>""", unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f"""<div class='kpi-card' style='border-top-color: {HEX_VIBRANT_BLUE};'>
        <h4>FBA Budget Spend</h4>
        <h2>${tot_spend:,.2f}</h2>
        <p>Blended Total Spend</p>
    </div>""", unsafe_allow_html=True)
with col_kpi3:
    st.markdown(f"""<div class='kpi-card' style='border-top-color: #2ECC71;'>
        <h4>FBA Total Sales</h4>
        <h2>${tot_sales:,.2f}</h2>
        <p>Total Revenue Captured</p>
    </div>""", unsafe_allow_html=True)
with col_kpi4:
    st.markdown(f"""<div class='kpi-card' style='border-top-color: #E67E22;'>
        <h4>Blended ACoS</h4>
        <h2>{global_acos:.2f}%</h2>
        <p>Total Spend / Total Sales</p>
    </div>""", unsafe_allow_html=True)
with col_kpi5:
    st.markdown(f"""<div class='kpi-card' style='border-top-color: {HEX_DARK_SLATE};'>
        <h4>Blended Funnel</h4>
        <h2>CTR: {global_ctr:.2f}%</h2>
        <p>CPC Median: ${global_cpc:.2f}</p>
    </div>""", unsafe_allow_html=True)

st.markdown("---")


# ---------------------------------------------------------------------------------
# 📊 CONTEXTUAL COLOR CONDITIONAL FORMATTING GENERATOR
# ---------------------------------------------------------------------------------
def style_comparison_matrix(df):
    """Applies clean operational cell highlighting to instantly surface performance deltas."""
    style_df = pd.DataFrame('', index=df.index, columns=df.columns)
    
    for idx in df.index:
        # Spend Logic: Higher spend is light red (cost leak), lower spend is light green
        if df.loc[idx, 'Spend (Prev)'] > df.loc[idx, 'Spend (This Wk)']:
            style_df.loc[idx, 'Spend (Prev)'] = 'background-color: #FADBD8'
            style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #D4EFDF'
        elif df.loc[idx, 'Spend (Prev)'] < df.loc[idx, 'Spend (This Wk)']:
            style_df.loc[idx, 'Spend (Prev)'] = 'background-color: #D4EFDF'
            style_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #FADBD8'
            
        # Sales Logic: Higher sales is green (growth traction), lower sales is red
        if df.loc[idx, 'Sales (Prev)'] > df.loc[idx, 'Sales (This Wk)']:
            style_df.loc[idx, 'Sales (Prev)'] = 'background-color: #D4EFDF'
            style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #FADBD8'
        elif df.loc[idx, 'Sales (Prev)'] < df.loc[idx, 'Sales (This Wk)']:
            style_df.loc[idx, 'Sales (Prev)'] = 'background-color: #FADBD8'
            style_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #D4EFDF'
            
        # ACoS Logic: Lower ACoS is green (increased efficiency), higher ACoS is red
        if df.loc[idx, 'ACoS % (Prev)'] > df.loc[idx, 'ACoS % (This Wk)']:
            style_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #FADBD8'
            style_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #D4EFDF'
        elif df.loc[idx, 'ACoS % (Prev)'] < df.loc[idx, 'ACoS % (This Wk)']:
            style_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #D4EFDF'
            style_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #FADBD8'
            
    return style_df


# ---------------------------------------------------------------------------------
# 💎 VISUAL USER INTERFACE PRODUCTION
# ---------------------------------------------------------------------------------
tabs = st.tabs(["📊 Portfolio Comparison Engine", "🏭 Vendor SKU Prefix Analytics"])

# ---------------------------------------------------------------------------------
# TAB 1: STRATEGIC PORTFOLIO COMPARISON
# ---------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("<span class='usecase-tag'>Strict FBA Mapped Portfolios (Non-Vizari)</span>", unsafe_allow_html=True)
    st.markdown("<div class='strategic-banner'><b>Strategic Portfolio Analytics:</b> Week-over-week efficiency metrics for portfolios containing <b>FBA</b>. Portfolios containing <b>VIZ / VIZARI</b> or non-FBA items are entirely excluded. Click column headers to sort values from lowest to highest.</div>", unsafe_allow_html=True)
    
    # Portfolio Aggregations
    p1_port = df_p1.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_port = df_p2.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    
    merged_port = pd.merge(p1_port, p2_port, on='Mapped Portfolio', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    
    merged_port['ACoS % (Prev)'] = np.where(merged_port['Sales (Prev)'] > 0, (merged_port['Spend (Prev)'] / merged_port['Sales (Prev)']) * 100, 0.0)
    merged_port['ACoS % (This Wk)'] = np.where(merged_port['Sales (This Wk)'] > 0, (merged_port['Spend (This Wk)'] / merged_port['Sales (This Wk)']) * 100, 0.0)
    
    # Column mapping structural adjustments
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
    
    # Target Export
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        final_port.to_excel(writer, sheet_name='Portfolio WBR', index=False)
    st.download_button(
        label="📥 Export Mapped Portfolio Sheet to Excel",
        data=towrite.getvalue(),
        file_name="Portfolio_WBR_Performance.xlsx",
        mime="application/vnd.ms-excel"
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Portfolio Pipeline Audit Logs")
    
    # Dynamic Expandable Inclusions Directory
    with st.expander("👀 Click to Expand: Included FBA Portfolios & Campaigns"):
        st.markdown("**The following active FBA portfolios and campaigns are built directly into your KPI calculations above:**")
        audit_inc = df_included_auditing.groupby(['Mapped Portfolio', 'Portfolio Name'])['Campaign Name'].unique().reset_index()
        for idx, row in audit_inc.iterrows():
            st.markdown(f"**📂 Segment:** `{row['Mapped Portfolio']}` | **Portfolio:** `{row['Portfolio Name']}` *({len(row['Campaign Name'])} campaigns)*")
            st.caption(", ".join(sorted(row['Campaign Name'])))
            
    # Dynamic Expandable Exclusions Directory
    with st.expander("❌ Click to Expand: Excluded Portfolios & Campaigns (FBM / Vizari / Non-FBA)"):
        st.markdown("**The following items failed the FBA validation engine criteria and were automatically omitted from the dashboard data matrix:**")
        if not df_excluded_auditing.empty:
            audit_exc = df_excluded_auditing.groupby('Portfolio Name')['Campaign Name'].unique().reset_index()
            for idx, row in audit_exc.iterrows():
                st.markdown(f"**🗑️ Removed Portfolio:** `{row['Portfolio Name']}` *({len(row['Campaign Name'])} campaigns)*")
                st.caption(", ".join(sorted(row['Campaign Name'])))
        else:
            st.info("No records match standard exclusion criteria.")

# ---------------------------------------------------------------------------------
# TAB 2: VENDOR BRAND PREFIX ANNOTATION
# ---------------------------------------------------------------------------------
with tabs[1]:
    st.markdown("<span class='usecase-tag'>Top 20 Brand Prefix SKU Matrix</span>", unsafe_allow_html=True)
    st.markdown("<div class='strategic-banner'><b>Prefix Brand Intelligence:</b> Extracts the leading 4 characters from product SKUs across the active FBA inventory pipeline. Limited to the <b>Top 20 high-revenue lines</b> this week. Click column headers to sort values from lowest to highest.</div>", unsafe_allow_html=True)
    
    # Safe isolation mapping
    df_p1 = df_p1.copy()
    df_p2 = df_p2.copy()
    df_p1['Brand Prefix'] = df_p1['SKU'].astype(str).str[:4].str.upper()
    df_p2['Brand Prefix'] = df_p2['SKU'].astype(str).str[:4].str.upper()
    
    p1_brand = df_p1.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_brand = df_p2.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    
    merged_brand = pd.merge(p1_brand, p2_brand, on='Brand Prefix', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    
    merged_brand['ACoS % (Prev)'] = np.where(merged_brand['Sales (Prev)'] > 0, (merged_brand['Spend (Prev)'] / merged_brand['Sales (Prev)']) * 100, 0.0)
    merged_brand['ACoS % (This Wk)'] = np.where(merged_brand['Sales (This Wk)'] > 0, (merged_brand['Spend (This Wk)'] / merged_brand['Sales (This Wk)']) * 100, 0.0)
    
    # Retain strictly top 20 lines by current week revenue metrics
    top_20_brands = merged_brand.sort_values(by='Sales (This Wk)', ascending=False).head(20).reset_index(drop=True)
    
    brand_order_cols = ['Brand Prefix', 'Spend (Prev)', 'Spend (This Wk)', 'Sales (Prev)', 'Sales (This Wk)', 'ACoS % (Prev)', 'ACoS % (This Wk)']
    final_brand = top_20_brands.reindex(columns=brand_order_cols).fillna(0.0)
    
    if not final_brand.empty:
        st.dataframe(
            final_brand.style.apply(style_comparison_matrix, axis=None).format({
                'Spend (Prev)': '${:,.2f}', 'Spend (This Wk)': '${:,.2f}',
                'Sales (Prev)': '${:,.2f}', 'Sales (This Wk)': '${:,.2f}',
                'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        # Dual Tab Master Consolidated Exporter Engine
        master_buffer = io.BytesIO()
        with pd.ExcelWriter(master_buffer, engine='xlsxwriter') as writer:
            final_port.to_excel(writer, sheet_name='Portfolio Performance WBR', index=False)
            final_brand.to_excel(writer, sheet_name='Vendor SKU WBR', index=False)
            
        st.download_button(
            label="📥 Export Complete Two-Tab Master WBR Report to Excel",
            data=master_buffer.getvalue(),
            file_name="Master_WBR_Comparison_Unified.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("No vendor records match current date range filters.")
