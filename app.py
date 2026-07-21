import streamlit as st
import pandas as pd
import numpy as np
import re
import io

# ------------------------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Sponsored Products WBR Console",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Sponsored Products Weekly Business Review (WBR) Console")
st.markdown("---")

# ------------------------------------------------------------------------------
# 1. CORE FBA & BUSINESS REPORT PARSERS
# ------------------------------------------------------------------------------

@st.cache_data
def load_core_fba_asins(fba_file):
    """Loads and normalizes the Core FBA ASIN master list."""
    try:
        fba_df = pd.read_excel(fba_file)
        return set(fba_df["ASIN"].dropna().astype(str).str.strip().str.upper())
    except Exception as e:
        return set()

def parse_currency(val):
    """Parses currency strings cleanly into floats."""
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(val_str)
    except:
        return 0.0

def process_business_report(br_file, core_fba_asins):
    """
    Parses uploaded Business Report, filters strictly by Core FBA ASINs,
    and returns both Standard Product Sales and Combined Additive Sales (Product + B2B).
    """
    if br_file.name.endswith(".csv"):
        df = pd.read_csv(br_file)
    else:
        df = pd.read_excel(br_file)

    child_col = [c for c in df.columns if "child" in c.lower() and "asin" in c.lower()]
    prod_sales_col = [c for c in df.columns if "ordered product sales" in c.lower() and "b2b" not in c.lower()]
    b2b_sales_col = [c for c in df.columns if "ordered product sales - b2b" in c.lower()]

    if not child_col or not prod_sales_col:
        st.error("Business Report must contain '(Child) ASIN' and 'Ordered Product Sales' columns.")
        return 0.0, 0.0, 0.0, df

    child_c = child_col[0]
    prod_c = prod_sales_col[0]
    b2b_c = b2b_sales_col[0] if b2b_sales_col else None

    df["Child_Clean"] = df[child_c].astype(str).str.strip().str.upper()
    df["Prod_Sales_Clean"] = df[prod_c].apply(parse_currency)
    df["B2B_Sales_Clean"] = df[b2b_c].apply(parse_currency) if b2b_c else 0.0

    # Filter by Core FBA ASIN list
    if core_fba_asins:
        fba_df = df[df["Child_Clean"].isin(core_fba_asins)].copy()
    else:
        fba_df = df.copy()

    total_fba_prod_sales = fba_df["Prod_Sales_Clean"].sum()
    total_fba_b2b_sales = fba_df["B2B_Sales_Clean"].sum()
    total_fba_combined_sales = total_fba_prod_sales + total_fba_b2b_sales

    return total_fba_prod_sales, total_fba_b2b_sales, total_fba_combined_sales, fba_df

# ------------------------------------------------------------------------------
# 2. SIDEBAR FILE UPLOADERS & SETTINGS
# ------------------------------------------------------------------------------

st.sidebar.header("📁 Data Source Uploads")

fba_master_file = st.sidebar.file_uploader("1. Core FBA ASIN Master List", type=["xlsx", "xls"])
br_file = st.sidebar.file_uploader("2. Business Report (CSV/Excel)", type=["csv", "xlsx"])
sp_file = st.sidebar.file_uploader("3. Sponsored Products Report (CSV/Excel)", type=["csv", "xlsx"])

st.sidebar.markdown("---")

# Load FBA Master List
if fba_master_file:
    core_fba_asins = load_core_fba_asins(fba_master_file)
    st.sidebar.success(f"Loaded {len(core_fba_asins):,} Core FBA ASINs")
else:
    core_fba_asins = load_core_fba_asins("Core FBA ASINs.xlsx")
    if core_fba_asins:
        st.sidebar.info(f"Using default Core FBA Master ({len(core_fba_asins):,} ASINs)")
    else:
        st.sidebar.warning("Upload 'Core FBA ASINs.xlsx' to filter FBA sales.")

# Process Business Report
fba_prod_sales = 0.0
fba_b2b_sales = 0.0
fba_combined_sales = 0.0
fba_filtered_df = pd.DataFrame()

if br_file:
    fba_prod_sales, fba_b2b_sales, fba_combined_sales, fba_filtered_df = process_business_report(br_file, core_fba_asins)

# ------------------------------------------------------------------------------
# 3. DASHBOARD CONSOLE ENGINE
# ------------------------------------------------------------------------------

if sp_file and br_file:
    # Read Sponsored Products Data
    if sp_file.name.endswith(".csv"):
        sp_df = pd.read_csv(sp_file)
    else:
        sp_df = pd.read_excel(sp_file)

    # Standardize Column Names
    spend_c = [c for c in sp_df.columns if "spend" in c.lower()][0]
    sales_c = [c for c in sp_df.columns if "sales" in c.lower() or "7 day total sales" in c.lower() or "14 day total sales" in c.lower()][0]
    clicks_c = [c for c in sp_df.columns if "click" in c.lower()][0]
    impr_c = [c for c in sp_df.columns if "impression" in c.lower()][0]
    port_c = [c for c in sp_df.columns if "portfolio" in c.lower()]
    camp_c = [c for c in sp_df.columns if "campaign" in c.lower()][0]
    country_c = [c for c in sp_df.columns if "country" in c.lower() or "marketplace" in c.lower()]

    # Parse standard metrics
    sp_df["Spend_Clean"] = sp_df[spend_c].apply(parse_currency)
    sp_df["Sales_Clean"] = sp_df[sales_c].apply(parse_currency)
    sp_df["Clicks_Clean"] = pd.to_numeric(sp_df[clicks_c].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    sp_df["Impressions_Clean"] = pd.to_numeric(sp_df[impr_c].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
    sp_df["Portfolio_Name"] = sp_df[port_c[0]].fillna("Unassigned") if port_c else "Unassigned"

    # --- COUNTRY FILTER IN SIDEBAR ---
    st.sidebar.header("🌍 Country Filter")
    if country_c:
        country_col_name = country_c[0]
        unique_countries = sorted(sp_df[country_col_name].dropna().unique())
        selected_country = st.sidebar.selectbox("Select Country", options=unique_countries)
        
        # Filter dataframe by single selected country
        country_sp_df = sp_df[sp_df[country_col_name] == selected_country].copy()
    else:
        st.sidebar.warning("No 'Country' column detected in Ad Report. Using full dataset.")
        country_sp_df = sp_df.copy()
        selected_country = "All Countries"

    # --- PORTFOLIO OMISSION RULES (PER COUNTRY) ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Portfolio Exclusion Rules")
    
    available_portfolios = sorted(country_sp_df["Portfolio_Name"].unique())
    exclude_keywords = st.sidebar.multiselect(
        f"Excluded Portfolio Keywords ({selected_country})",
        options=["Vizari", "FBM", "CBT", "Ageing", "Exclusive"],
        default=["Vizari", "FBM", "CBT", "Ageing"]
    )

    # Routing Engine: Exclude specified Portfolios for selected country
    pattern = "|".join([re.escape(k) for k in exclude_keywords]) if exclude_keywords else "a^"
    included_sp_df = country_sp_df[~country_sp_df["Portfolio_Name"].str.contains(pattern, case=False, regex=True)].copy()
    excluded_sp_df = country_sp_df[country_sp_df["Portfolio_Name"].str.contains(pattern, case=False, regex=True)].copy()

    # Core Metrics Calculations (Country-Specific)
    total_ad_spend = included_sp_df["Spend_Clean"].sum()
    total_ad_sales = included_sp_df["Sales_Clean"].sum()
    total_clicks = included_sp_df["Clicks_Clean"].sum()
    total_impressions = included_sp_df["Impressions_Clean"].sum()

    acos_pct = (total_ad_spend / total_ad_sales * 100) if total_ad_sales > 0 else 0.0
    tacos_pct = (total_ad_spend / fba_combined_sales * 100) if fba_combined_sales > 0 else 0.0
    ctr_pct = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
    cpc = (total_ad_spend / total_clicks) if total_clicks > 0 else 0.0

    # Display Sidebar Summary Metrics for Selected Country
    st.sidebar.markdown("---")
    st.sidebar.metric(f"Ad Spend ({selected_country})", f"${total_ad_spend:,.2f}")
    st.sidebar.metric(f"Ad Sales ({selected_country})", f"${total_ad_sales:,.2f}")

    # Dynamic KPI Ribbon
    st.markdown(f"### Current View: **{selected_country}**")
    kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
    kpi1.metric("Total FBA Sales", f"${fba_combined_sales:,.2f}")
    kpi2.metric("Total Ad Spend", f"${total_ad_spend:,.2f}")
    kpi3.metric("Total Ad Sales", f"${total_ad_sales:,.2f}")
    kpi4.metric("ACoS (%)", f"{acos_pct:.2f}%")
    kpi5.metric("TACoS (%) 🎯", f"{tacos_pct:.2f}%")
    kpi6.metric("Avg. CPC", f"${cpc:.2f}")

    st.markdown("---")

    # --------------------------------------------------------------------------
    # MULTI-TAB NAVIGATION CONSOLE
    # --------------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📌 Executive Overview",
        "🏷️ Portfolio Performance",
        "🔤 Brand Prefix Analytics",
        "💡 Automated Strategy Insights",
        "📋 Business Report Audit",
        "🛡️ Excluded Campaign Log"
    ])

    # --- TAB 1: EXECUTIVE OVERVIEW ---
    with tab1:
        st.subheader(f"Executive WBR Performance Summary ({selected_country})")
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### 💰 Sales & TACoS Structure")
            summary_tbl = pd.DataFrame({
                "Metric": [
                    "FBA Ordered Product Sales",
                    "FBA B2B Product Sales",
                    "Total FBA Combined Sales",
                    "Sponsored Products Ad Spend",
                    "Sponsored Products Ad Sales",
                    "Blended ACoS (%)",
                    "Blended TACoS (%)"
                ],
                "Value": [
                    f"${fba_prod_sales:,.2f}",
                    f"${fba_b2b_sales:,.2f}",
                    f"${fba_combined_sales:,.2f}",
                    f"${total_ad_spend:,.2f}",
                    f"${total_ad_sales:,.2f}",
                    f"{acos_pct:.2f}%",
                    f"{tacos_pct:.2f}%"
                ]
            })
            st.table(summary_tbl)

        with col_right:
            st.markdown("#### 📈 Traffic & Efficiency Metrics")
            traffic_tbl = pd.DataFrame({
                "Metric": [
                    "Total Impressions",
                    "Total Clicks",
                    "Click-Through Rate (CTR %)",
                    "Cost Per Click (CPC)",
                    "Ad Sales Share of Total FBA Sales"
                ],
                "Value": [
                    f"{int(total_impressions):,}",
                    f"{int(total_clicks):,}",
                    f"{ctr_pct:.2f}%",
                    f"${cpc:.2f}",
                    f"{(total_ad_sales / fba_combined_sales * 100):.2f}%" if fba_combined_sales > 0 else "0.00%"
                ]
            })
            st.table(traffic_tbl)

    # --- TAB 2: PORTFOLIO PERFORMANCE ---
    with tab2:
        st.subheader(f"Portfolio Segmentation & TACoS Contribution ({selected_country})")
        
        port_df = included_sp_df.groupby("Portfolio_Name").agg(
            Ad_Spend=("Spend_Clean", "sum"),
            Ad_Sales=("Sales_Clean", "sum"),
            Clicks=("Clicks_Clean", "sum"),
            Impressions=("Impressions_Clean", "sum")
        ).reset_index()

        port_df["ACoS %"] = np.where(port_df["Ad_Sales"] > 0, (port_df["Ad_Spend"] / port_df["Ad_Sales"]) * 100, 0)
        port_df["Share of Ad Spend %"] = (port_df["Ad_Spend"] / total_ad_spend * 100) if total_ad_spend > 0 else 0
        port_df["TACoS Contribution %"] = np.where(fba_combined_sales > 0, (port_df["Ad_Spend"] / fba_combined_sales) * 100, 0)

        # Formatting
        port_display = port_df.copy()
        port_display["Ad_Spend"] = port_display["Ad_Spend"].map("${:,.2f}".format)
        port_display["Ad_Sales"] = port_display["Ad_Sales"].map("${:,.2f}".format)
        port_display["ACoS %"] = port_display["ACoS %"].map("{:.2f}%".format)
        port_display["Share of Ad Spend %"] = port_display["Share of Ad Spend %"].map("{:.2f}%".format)
        port_display["TACoS Contribution %"] = port_display["TACoS Contribution %"].map("{:.2f}%".format)

        st.dataframe(port_display, use_container_width=True)

    # --- TAB 3: BRAND PREFIX ANALYTICS ---
    with tab3:
        st.subheader(f"Brand Prefix Breakdown ({selected_country})")
        
        included_sp_df["Brand_Prefix"] = included_sp_df[camp_c].astype(str).str.extract(r"^([A-Za-z0-9]{4})_")[0].str.upper().fillna("OTHER")

        prefix_df = included_sp_df.groupby("Brand_Prefix").agg(
            Ad_Spend=("Spend_Clean", "sum"),
            Ad_Sales=("Sales_Clean", "sum"),
            Clicks=("Clicks_Clean", "sum")
        ).reset_index().sort_values(by="Ad_Spend", ascending=False)

        prefix_df["ACoS %"] = np.where(prefix_df["Ad_Sales"] > 0, (prefix_df["Ad_Spend"] / prefix_df["Ad_Sales"]) * 100, 0)
        prefix_df["Share of Ad Spend %"] = (prefix_df["Ad_Spend"] / total_ad_spend * 100) if total_ad_spend > 0 else 0

        # Formatting
        prefix_display = prefix_df.copy()
        prefix_display["Ad_Spend"] = prefix_display["Ad_Spend"].map("${:,.2f}".format)
        prefix_display["Ad_Sales"] = prefix_display["Ad_Sales"].map("${:,.2f}".format)
        prefix_display["ACoS %"] = prefix_display["ACoS %"].map("{:.2f}%".format)
        prefix_display["Share of Ad Spend %"] = prefix_display["Share of Ad Spend %"].map("{:.2f}%".format)

        st.dataframe(prefix_display.head(25), use_container_width=True)

    # --- TAB 4: AUTOMATED STRATEGY INSIGHTS ---
    with tab4:
        st.subheader(f"💡 Automated Optimization Insights ({selected_country})")

        high_spend_no_sales = included_sp_df[(included_sp_df["Spend_Clean"] > 50) & (included_sp_df["Sales_Clean"] == 0)]
        high_acos_camps = included_sp_df[(included_sp_df["Sales_Clean"] > 0) & ((included_sp_df["Spend_Clean"] / included_sp_df["Sales_Clean"]) > 0.60)]

        st.markdown(f"• **Wasted Spend Alert:** Identified **{len(high_spend_no_sales)} campaigns** with > $50 spend and zero sales, totaling **${high_spend_no_sales['Spend_Clean'].sum():,.2f}** in wasted spend.")
        st.markdown(f"• **High ACoS Warning:** **{len(high_acos_camps)} campaigns** are running at > 60% ACoS.")

        if tacos_pct > 15.0:
            st.warning(f"⚠️ **High TACoS Warning:** Current TACoS is **{tacos_pct:.2f}%**, exceeding the 15% target threshold. Review high ACoS targets.")
        else:
            st.success(f"✅ **Healthy TACoS:** Current TACoS is **{tacos_pct:.2f}%**, well within sustainable efficiency limits.")

    # --- TAB 5: BUSINESS REPORT AUDIT ---
    with tab5:
        st.subheader("📋 Core FBA Business Report Audit")
        st.write(f"Matched **{len(fba_filtered_df):,}** active Child ASINs from the uploaded Business Report.")

        st.dataframe(
            fba_filtered_df[["Child_Clean", "Prod_Sales_Clean", "B2B_Sales_Clean"]].rename(
                columns={
                    "Child_Clean": "Child ASIN",
                    "Prod_Sales_Clean": "Ordered Product Sales ($)",
                    "B2B_Sales_Clean": "Ordered Product Sales - B2B ($)"
                }
            ),
            use_container_width=True
        )

    # --- TAB 6: EXCLUDED CAMPAIGN LOG ---
    with tab6:
        st.subheader(f"🛡️ Excluded Portfolios Audit Log ({selected_country})")
        st.write(f"Isolated **{len(excluded_sp_df):,}** campaign rows in **{selected_country}** based on keywords: `{exclude_keywords}`")

        if len(excluded_sp_df) > 0:
            st.dataframe(
                excluded_sp_df[["Portfolio_Name", camp_c, "Spend_Clean", "Sales_Clean"]].rename(
                    columns={camp_c: "Campaign Name", "Spend_Clean": "Ad Spend ($)", "Sales_Clean": "Ad Sales ($)"}
                ),
                use_container_width=True
            )
        else:
            st.info("No campaigns matched the exclusion criteria for this country.")

else:
    st.info("👈 Please upload the **Business Report** and **Sponsored Products Report** in the sidebar to activate the console.")
