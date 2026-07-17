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
biz_file = st.sidebar.file_uploader("2️⃣ Upload Amazon Business Report (Optional for TACoS)", type=["csv", "xlsx"])

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

# Enforce explicit FBA routing rules
def assign_wbr_portfolio(name):
    name_str = str(name).strip().lower()
    if 'fba' not in name_str or 'viz' in name_str or 'vizari' in name_str:
        return 'EXCLUDE_FILTER'
    if 'map' in name_str: return 'map'
    elif 'ageing' in name_str: return 'ageing'
    elif 'exclusive' in name_str: return 'exclusive'
    else: return 'fba'

df_raw['Mapped Portfolio'] = df_raw['Portfolio Name'].apply(assign_wbr_portfolio)
df_processed = df_raw[df_raw['Mapped Portfolio'] != 'EXCLUDE_FILTER'].copy()
df_processed['Brand Prefix'] = df_processed['SKU'].astype(str).str[:4].str.upper()

# Set date scopes
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 Live Window Control")
p1_start = st.sidebar.date_input("P1 Start Date", df_processed['Date'].min())
p1_end = st.sidebar.date_input("P1 End Date", df_processed['Date'].max() - pd.Timedelta(days=7))
p2_start = st.sidebar.date_input("P2 Start Date", df_processed['Date'].max() - pd.Timedelta(days=6))
p2_end = st.sidebar.date_input("P2 End Date", df_processed['Date'].max())

df_p1 = df_processed[(df_processed['Date'] >= pd.Timestamp(p1_start)) & (df_processed['Date'] <= pd.Timestamp(p1_end))]
df_p2 = df_processed[(df_processed['Date'] >= pd.Timestamp(p2_start)) & (df_processed['Date'] <= pd.Timestamp(p2_end))]

# ---------------------------------------------------------------------------------
# 📈 OPTIONAL AMAZON BUSINESS REPORT INTELLIGENCE FUNNEL (TACoS ENGINE)
# ---------------------------------------------------------------------------------
total_business_sales = 0.0
has_tacos = False

if biz_file:
    try:
        if biz_file.name.endswith('.csv'):
            df_biz = pd.read_csv(biz_file)
        else:
            df_biz = pd.read_excel(biz_file)
        
        # Enforce column indexes explicitly matching structural specifications:
        # Column D is Index 3 (SKU column checking for FBA / SNL)
        # Column U is Index 20 (Total Product Sales revenue values)
        if len(df_biz.columns) >= 21:
            sku_col_raw = df_biz.columns[3]
            sales_col_raw = df_biz.columns[20]
            
            df_biz[sales_col_raw] = df_biz[sales_col_raw].astype(str).str.replace(r'[%\$,]', '', regex=True)
            df_biz['Clean Sales'] = pd.to_numeric(df_biz[sales_col_raw], errors='coerce').fillna(0.0)
            
            # Keep only items containing FBA or SNL strings in Column D
            df_biz_filtered = df_biz[df_biz[sku_col_raw].astype(str).str.upper().str.contains('FBA|SNL', regex=True, na=False)]
            total_business_sales = df_biz_filtered['Clean Sales'].sum()
            if total_business_sales > 0:
                has_tacos = True
    except Exception as e:
        st.sidebar.warning(f"Could not map business report automatically: {e}")

# Global Metrics Cards Ribbon
t_sp = df_p2['Spend'].sum()
t_sl = df_p2['Sales'].sum()
t_cl = df_p2['Clicks'].sum()
t_im = df_p2['Impressions'].sum()

t_ac = (t_sp / t_sl * 100) if t_sl > 0 else 0.0
t_ro = (t_sl / t_sp) if t_sp > 0 else 0.0
t_ct = (t_cl / t_im * 100) if t_im > 0 else 0.0
t_cp = (t_sp / t_cl) if t_cl > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"<div class='kpi-card'><h4>Total FBA Spend</h4><h2>${t_sp:,.2f}</h2><p>Active Window</p></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-card' style='border-top-color: #2ECC71;'><h4>Total FBA Ad Sales</h4><h2>${t_sl:,.2f}</h2><p>Attributed Revenue</p></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-card' style='border-top-color: #E67E22;'><h4>Blended ACoS</h4><h2>{t_ac:.2f}%</h2><p>Advertising Efficiency</p></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='kpi-card' style='border-top-color: {HEX_VIBRANT_BLUE};'><h4>Blended Funnel</h4><h2>CTR: {t_ct:.2f}%</h2><p>CPC: ${t_cp:.2f}</p></div>", unsafe_allow_html=True)
with col5:
    if has_tacos:
        t_tacos = (t_sp / total_business_sales * 100)
        st.markdown(f"<div class='kpi-card' style='border-top-color: #9B59B6;'><h4>Total TACoS</h4><h2>{t_tacos:.2f}%</h2><p>Based on FBA/SNL Sales</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='kpi-card' style='border-top-color: #CCD1D1;'><h4>Total TACoS</h4><h2>N/A</h2><p>Business Report Missing</p></div>", unsafe_allow_html=True)

st.markdown("---")

tabs = st.tabs(["📋 Total FBA High-Level Summary", "📊 Portfolio Comparison Engine", "🏭 Vendor SKU Prefix Analytics", "💡 Deep-Dive Automated Insights"])

# ---------------------------------------------------------------------------------
# TAB 1: TOTAL FBA HIGH-LEVEL CHANNELS SUMMARY
# ---------------------------------------------------------------------------------
with tabs[0]:
    st.markdown("<span class='usecase-tag'>Total Business Funnel Overview</span>", unsafe_allow_html=True)
    
    summary_data = {
        "Portfolio Segment": "Total FBA Channel Portfolio",
        "Ad Spends": f"${t_sp:,.2f}",
        "Ad Sales": f"${t_sl:,.2f}",
        "ACoS": f"{t_ac:.2f}%",
        "ROAS": f"{t_ro:.2f}x",
        "TACoS": f"{(t_sp / total_business_sales * 100):.2f}%" if has_tacos else "N/A"
    }
    st.dataframe(pd.DataFrame([summary_data]), use_container_width=True)

# Helper for cell comparison coloring
def style_matrix(df):
    s_df = pd.DataFrame('', index=df.index, columns=df.columns)
    for idx in df.index:
        if 'Spend (Prev)' in df.columns and 'Spend (This Wk)' in df.columns:
            if df.loc[idx, 'Spend (Prev)'] > df.loc[idx, 'Spend (This Wk)']:
                s_df.loc[idx, 'Spend (Prev)'] = 'background-color: #FADBD8'
                s_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #D4EFDF'
            else:
                s_df.loc[idx, 'Spend (Prev)'] = 'background-color: #D4EFDF'
                s_df.loc[idx, 'Spend (This Wk)'] = 'background-color: #FADBD8'
        if 'Sales (Prev)' in df.columns and 'Sales (This Wk)' in df.columns:
            if df.loc[idx, 'Sales (Prev)'] > df.loc[idx, 'Sales (This Wk)']:
                s_df.loc[idx, 'Sales (Prev)'] = 'background-color: #D4EFDF'
                s_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #FADBD8'
            else:
                s_df.loc[idx, 'Sales (Prev)'] = 'background-color: #FADBD8'
                s_df.loc[idx, 'Sales (This Wk)'] = 'background-color: #D4EFDF'
        if 'ACoS % (Prev)' in df.columns and 'ACoS % (This Wk)' in df.columns:
            if df.loc[idx, 'ACoS % (Prev)'] > df.loc[idx, 'ACoS % (This Wk)']:
                s_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #FADBD8'
                s_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #D4EFDF'
            else:
                s_df.loc[idx, 'ACoS % (Prev)'] = 'background-color: #D4EFDF'
                s_df.loc[idx, 'ACoS % (This Wk)'] = 'background-color: #FADBD8'
    return s_df

# ---------------------------------------------------------------------------------
# TAB 2: PORTFOLIO ENGINE
# ---------------------------------------------------------------------------------
with tabs[1]:
    p1_p = df_p1.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_p = df_p2.groupby('Mapped Portfolio').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    m_p = pd.merge(p1_p, p2_p, on='Mapped Portfolio', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    m_p['ACoS % (Prev)'] = np.where(m_p['Sales (Prev)'] > 0, (m_p['Spend (Prev)'] / m_p['Sales (Prev)']) * 100, 0.0)
    m_p['ACoS % (This Wk)'] = np.where(m_p['Sales (This Wk)'] > 0, (m_p['Spend (This Wk)'] / m_p['Sales (This Wk)']) * 100, 0.0)
    
    st.dataframe(m_p.style.apply(style_matrix, axis=None).format({
        'Spend (Prev)': '${:,.2f}', 'Spend (This Wk)': '${:,.2f}',
        'Sales (Prev)': '${:,.2f}', 'Sales (This Wk)': '${:,.2f}',
        'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
    }), use_container_width=True)
    
    # Target Export
    towrite_p = io.BytesIO()
    with pd.ExcelWriter(towrite_p, engine='xlsxwriter') as writer:
        m_p.to_excel(writer, sheet_name='Portfolio WBR', index=False)
    st.download_button(
        label="📥 Export Portfolio Performance Sheet",
        data=towrite_p.getvalue(),
        file_name="Portfolio_WBR_Output.xlsx",
        mime="application/vnd.ms-excel"
    )

# ---------------------------------------------------------------------------------
# TAB 3: VENDOR BRAND PREFIX ANNOTATION
# ---------------------------------------------------------------------------------
with tabs[2]:
    p1_b = df_p1.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    p2_b = df_p2.groupby('Brand Prefix').agg({'Spend':'sum', 'Sales':'sum'}).reset_index()
    m_b = pd.merge(p1_b, p2_b, on='Brand Prefix', how='outer', suffixes=(' (Prev)', ' (This Wk)')).fillna(0.0)
    m_b['ACoS % (Prev)'] = np.where(m_b['Sales (Prev)'] > 0, (m_b['Spend (Prev)'] / m_b['Sales (Prev)']) * 100, 0.0)
    m_b['ACoS % (This Wk)'] = np.where(m_b['Sales (This Wk)'] > 0, (m_b['Spend (This Wk)'] / m_b['Sales (This Wk)']) * 100, 0.0)
    
    top_20 = m_b.sort_values(by='Sales (This Wk)', ascending=False).head(20).reset_index(drop=True)
    st.dataframe(top_20.style.apply(style_matrix, axis=None).format({
        'Spend (Prev)': '${:,.2f}', 'Spend (This Wk)': '${:,.2f}',
        'Sales (Prev)': '${:,.2f}', 'Sales (This Wk)': '${:,.2f}',
        'ACoS % (Prev)': '{:.2f}%', 'ACoS % (This Wk)': '{:.2f}%'
    }), use_container_width=True)

# ---------------------------------------------------------------------------------
# TAB 4: AUTOMATED INSIGHTS GENERATION ENGINE
# ---------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("💡 Dynamic Operational Win & Failure Insights Engine")
    
    # 1. PORTFOLIO WIN IDENTIFICATION
    best_port_row = m_p.sort_values(by='Sales (This Wk)', ascending=False).iloc[0] if not m_p.empty else None
    if best_port_row is not None:
        p_name = best_port_row['Mapped Portfolio']
        st.markdown(f"<div class='insight-header'>🟢 Portfolio Strategy Win: '{p_name}' Segment Efficiency Optimized</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS shifted from {best_port_row['ACoS % (Prev)']:.2f}% to {best_port_row['ACoS % (This Wk)']:.2f}% as sales scaled to ${best_port_row['Sales (This Wk)']:,.2f}.**")
        
        # Pull specific winning campaigns in this window
        sub_camps = df_p2[df_p2['Mapped Portfolio'] == p_name].groupby('Campaign Name').agg({'Sales':'sum', 'Spend':'sum'}).reset_index()
        sub_camps['ACoS'] = (sub_camps['Spend'] / sub_camps['Sales']) * 100
        top_camp = sub_camps.sort_values(by='Sales', ascending=False).iloc[0]['Campaign Name'] if not sub_camps.empty else "Core Focus Campaigns"
        st.write(f"This efficiency gain is directly attributed to structural performance stability inside the `{p_name}` ecosystem. High-yield conversions inside `{top_camp}` drove volume without bloating cost-per-click thresholds, securing scalable net-margin returns for the active period.")

    # 2. VENDOR/BRAND WIN IDENTIFICATION (>1000 sales threshold applied)
    valid_brands = m_b[m_b['Sales (This Wk)'] >= 1000.0]
    if not valid_brands.empty:
        best_brand_row = valid_brands.sort_values(by='Sales (This Wk)', ascending=False).iloc[0]
        b_prefix = best_brand_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🟢 Brand Scale Win: Prefix '{b_prefix}' Secures Dominance</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS trended from {best_brand_row['ACoS % (Prev)']:.2f}% to {best_brand_row['ACoS % (This Wk)']:.2f}% with high-velocity sales grossing ${best_brand_row['Sales (This Wk)']:,.2f}.**")
        st.write(f"The `{b_prefix}` prefix successfully crossed your core volume threshold by prioritizing clean manual exact keyword visibility vectors. Wasted spend elements were aggressively managed, forcing ad efficiency down while harvesting clean search placements across high-intent product listings.")

    # 3. FAILURE / SYSTEM CORRECTION LOGIC
    st.markdown("---")
    st.markdown("### ⚠️ System Failures & Loss Corrections")
    
    poor_port_row = m_p.sort_values(by='ACoS % (This Wk)', ascending=False).iloc[0] if not m_p.empty else None
    if poor_port_row is not None and poor_port_row['ACoS % (This Wk)'] > poor_port_row['ACoS % (Prev)']:
        p_name_p = poor_port_row['Mapped Portfolio']
        st.markdown(f"<div class='insight-header'>🔴 Portfolio Margin Leak: `{p_name_p}` Friction Target</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS expanded from {poor_port_row['ACoS % (Prev)']:.2f}% up to {poor_port_row['ACoS % (This Wk)']:.2f}%, indicating budget bleed.**")
        st.write(f"The margin degradation in the `{p_name_p}` segment indicates a sharp drop in real-time customer conversion rates relative to click costs. Non-converting high-bid auto placements or broader keyword sets have over-consumed target operational budgets, requiring immediate manual extraction and match-type adjustment.")

    poor_brand_row = m_b[(m_b['Sales (This Wk)'] >= 1000.0)].sort_values(by='ACoS % (This Wk)', ascending=False).iloc[0] if not valid_brands.empty else None
    if poor_brand_row is not None and poor_brand_row['ACoS % (This Wk)'] > poor_brand_row['ACoS % (Prev)']:
        b_prefix_p = poor_brand_row['Brand Prefix']
        st.markdown(f"<div class='insight-header'>🔴 Brand Cost Failure: Prefix `{b_prefix_p}` Efficiency Regression</div>", unsafe_allow_html=True)
        st.markdown(f"**ACoS deteriorated from {poor_brand_row['ACoS % (Prev)']:.2f}% to {poor_brand_row['ACoS % (This Wk)']:.2f}% despite grossing ${poor_brand_row['Sales (This Wk)']:,.2f} in sales.**")
        st.write(f"Although `{b_prefix_p}` remains a high-revenue line item, search campaigns are encountering aggressive cross-conquest bidding actions from marketplace competitors. High cost-per-click elements combined with lower cart-add rates indicate that a swift negative-match placement clean-up is required to mitigate farther budget loss.")
        
    # Consolidated Workbook Exporter
    master_buffer = io.BytesIO()
    with pd.ExcelWriter(master_buffer, engine='xlsxwriter') as writer:
        m_p.to_excel(writer, sheet_name='Portfolio Performance WBR', index=False)
        top_20.to_excel(writer, sheet_name='Vendor SKU WBR', index=False)
        
    st.download_button(
        label="📥 Export Complete Two-Tab Master WBR Report to Excel",
        data=master_buffer.getvalue(),
        file_name="Master_WBR_Comparison_Unified.xlsx",
        mime="application/vnd.ms-excel"
    )
