import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib # Restored for fuzzy matching

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI Calculator", layout="wide", page_icon="💼")

# --- CUSTOM CSS FOR POLISH ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    .success-box { padding: 15px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px; }
    .error-box { padding: 15px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 1. HARDCODED PRICE BOOK ---
# Using the list you provided. 
# Note: We assume Year 2 Price = Year 1 Price for this model since Y2 data wasn't provided yet.
PRICE_CATALOG = {
    # Standard Items
    "Plumbing and Drainage Plus": 12.00,
    "Plumbing and Electrics": 48.00,
    "Heating, Plumbing and Electrics Plus": 216.00,
    "Heating, Plumbing and Electrics": 192.00,
    "Heating and Plumbing": 174.00,
    "Gas Boiler and Central Heating": 162.00,
    "Electrics": 36.00,
    "Gas Boiler": 108.00,
    "Gas Boiler service": 108.00,
    # Landlords
    "Landlord's Plumbing and Drainage Plus": 12.00,
    "Landlord’s Electrics": 60.00,
    "Landlord's Plumbing and Electrics": 72.00,
    "Landlord’s Gas Boiler": 132.00,
    "Landlord’s Gas Boiler and Central Heating": 198.00,
    "Landlord’s Heating and Plumbing": 210.00,
    "Landlord’s Heating, Plumbing and Electrics": 246.00,
    "Landlord’s Heating, Plumbing and Electrics Plus": 270.00,
    "Landlord’s Gas Safety Certificate": 108.00,
    # Promotions (Appended 'Promo' to differentiate duplicate keys)
    "Plumbing and Drainage Plus (Promo)": 6.00,
    "Plumbing and Electrics (Promo)": 42.00,
    "Landlord's Plumbing and Drainage Plus (Promo)": 6.00,
    "Landlord’s Plumbing and Electrics (Promo)": 66.00
}

# --- HELPER: FUZZY PARSING LOGIC ---
def parse_paste_data(raw_text):
    """
    Parses pasted text, finds prices, and handles typos using fuzzy matching.
    """
    parsed_rows = []
    if not raw_text: return pd.DataFrame()
    
    lines = raw_text.strip().split('\n')
    for line in lines:
        # Split logic (Tab, Comma, or Space)
        if '\t' in line: parts = line.split('\t')
        elif ',' in line: parts = line.split(',')
        else: parts = line.rsplit(' ', 1)

        if len(parts) >= 2:
            p_name = parts[0].strip()
            # Clean number string (remove £, commas)
            p_count_str = parts[1].strip().replace(',', '').replace('£', '')
            try: p_count = float(p_count_str)
            except: p_count = 0
            
            # --- INTELLIGENT MATCHING ---
            matched_price = 0
            status = "⚠️ Price Not Found"
            match_name = p_name

            # 1. Exact Match
            if p_name in PRICE_CATALOG:
                matched_price = PRICE_CATALOG[p_name]
                status = "✅ Exact"
            else:
                # 2. Case Insensitive
                found = False
                for cat_name, cat_price in PRICE_CATALOG.items():
                    if p_name.lower() == cat_name.lower():
                        matched_price = cat_price
                        match_name = cat_name
                        status = "✅ Exact (Case Fixed)"
                        found = True
                        break
                
                # 3. Fuzzy Match (The "Typo Fixer")
                if not found:
                    # Look for closest string match in catalog
                    matches = difflib.get_close_matches(p_name, PRICE_CATALOG.keys(), n=1, cutoff=0.6)
                    if matches:
                        match_name = matches[0]
                        matched_price = PRICE_CATALOG[match_name]
                        status = f"⚡ Fuzzy Match: {match_name}"
            
            parsed_rows.append({
                "Original Input": p_name,
                "Matched Policy": match_name,
                "Count": p_count,
                "Price": matched_price,
                "Status": status
            })
            
    return pd.DataFrame(parsed_rows)

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### Evaluate the financial impact of A/B tests across multiple variants.")

with st.expander("📘 **Start Here: How to use this tool**", expanded=True):
    st.markdown("""
    **Who is this for?** Executives and Strategy Leads.
    **What does it do?** It tells you if your new strategy makes money, even if the conversion rate looks different.
    
    1.  **Define Variants (Sidebar):** Select how many test groups you had (e.g., Control + Variant 1).
    2.  **Paste Data (Tabs):** For each tab, copy the product mix (Name | Count) directly from Excel and paste it in.
    3.  **Check the Match:** The tool uses AI logic to fix typos (e.g., "Gas Blr" -> "Gas Boiler").
    4.  **Review Results:** Scroll down to the Executive Summary for the final recommendation.
    """)

# --- SIDEBAR: SETTINGS & GLOSSARY ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    
    # Dynamic Variants
    num_variants = st.number_input("Number of New Variants", min_value=1, max_value=5, value=1, 
                                  help="How many different versions did you test against the Control?")
    variant_names = [f"Variant {i+1}" for i in range(num_variants)]
    
    st.divider()
    st.subheader("Market Assumptions")
    traffic = st.number_input("Traffic per Variant", value=10000, step=1000, 
                             help="How many visitors were in each group?")
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500,
                          help="Total cost to build/market this strategy.")
    retention = st.slider("Year 2 Renewal Rate", 50, 95, 80, format="%d%%",
                         help="% of customers who renew next year.") / 100.0

    st.divider()
    st.markdown("### 📚 Glossary")
    st.markdown("""
    * **LTV (Lifetime Value):** Total cash value of one customer over 2 years.
    * **Blended Price:** The average price paid, accounting for the mix of cheap vs. expensive products.
    * **ROI:** Return on Investment. (Net Profit / Cost).
    """)

# --- SECTION 1: PRODUCT MIX INPUTS ---
st.header("1. Input Test Data")
st.info("Paste your Excel data below. We automatically clean typos and look up prices.")

tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])
results_data = {} 

# --- TAB LOGIC (Iterate through Control + Variants) ---
all_groups = ["Control"] + variant_names

for i, group_name in enumerate(all_groups):
    with tabs[i]:
        col_input, col_check, col_metrics = st.columns([1.5, 2, 1])
        
        # 1. INPUT
        with col_input:
            st.markdown(f"**Paste {group_name} Mix** (Name | Count)")
            raw_paste = st.text_area(f"Input for {group_name}", height=200, key=f"paste_{group_name}", 
                                    placeholder="Plumbing...\t50\nGas Boiler\t20")
            
            # Conversion Rate Input for this group
            cr_val = st.number_input(f"{group_name} Conversion Rate (%)", value=2.0 if i==0 else 2.2, 
                                    format="%.2f", key=f"cr_{group_name}", 
                                    help="The final conversion rate observed in the test.") / 100

        # 2. PROCESSING
        df = parse_paste_data(raw_paste)
        
        if not df.empty:
            # Calculate Mix & LTV
            total_sales = df["Count"].sum()
            df["Mix %"] = df["Count"] / total_sales
            
            # LTV Calculation: Year 1 Price + (Year 1 Price * Retention)
            # (Assuming Y2 Price = Y1 Price as per instructions)
            df["Item LTV"] = df["Price"] + (df["Price"] * retention)
            
            # Blended Metrics
            blended_ltv = (df["Item LTV"] * df["Mix %"]).sum()
            avg_y1 = (df["Price"] * df["Mix %"]).sum()
            
            total_revenue = traffic * cr_val * blended_ltv
            
            # Store for Comparison
            results_data[group_name] = {
                "CR": cr_val,
                "LTV": blended_ltv,
                "Revenue": total_revenue,
                "AvgPrice": avg_y1
            }

            # 3. DATA PREVIEW (With Status Checks)
            with col_check:
                st.markdown("**Data Validation**")
                st.dataframe(
                    df[["Matched Policy", "Count", "Price", "Status"]],
                    column_config={
                        "Price": st.column_config.NumberColumn(format="£%.2f"),
                        "Status": st.column_config.TextColumn(help="Did we find the price in the catalog?"),
                    },
                    hide_index=True,
                    height=200,
                    use_container_width=True
                )
                # Warn about zeros
                if (df["Price"] == 0).any():
                    st.warning("⚠️ Some items have £0 price. Check for spelling errors in the 'Status' column.")

            # 4. INSTANT METRICS
            with col_metrics:
                st.markdown("**Group Performance**")
                st.metric("Blended LTV", f"£{blended_ltv:.2f}", help="Avg value per customer (2 Years)")
                st.metric("Proj. Revenue", f"£{total_revenue:,.0f}", help="Traffic x CR x LTV")
        
        else:
            with col_check:
                st.info(f"👈 Waiting for data for {group_name}...")

# --- SECTION 2: EXECUTIVE SUMMARY ---
if "Control" in results_data and len(results_data) > 1:
    st.divider()
    st.header("2. Executive Summary & Recommendation")
    
    # Find the winner
    best_variant = max(results_data, key=lambda x: results_data[x]['Revenue'] if x != 'Control' else -1)
    
    base_rev = results_data["Control"]["Revenue"]
    best_rev = results_data[best_variant]["Revenue"]
    incremental = best_rev - base_rev
    net_profit = incremental - cost
    roi = (net_profit / cost) * 100 if cost > 0 else 0
    
    # 1. THE NARRATIVE
    if net_profit > 0:
        st.markdown(f"""
        <div class="success-box">
            <h3 style="margin:0">✅ Recommendation: Implement {best_variant}</h3>
            <p style="margin:0">This strategy is projected to generate <b>£{net_profit:,.0f}</b> in pure profit over 2 years. 
            The ROI is <b>{roi:.0f}%</b>.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
         st.markdown(f"""
        <div class="error-box">
            <h3 style="margin:0">⚠️ Recommendation: Do Not Roll Out</h3>
            <p style="margin:0">Even though {best_variant} might have different metrics, after accounting for costs, 
            it is projected to <b>lose £{abs(net_profit):,.0f}</b>.</p>
        </div>
        """, unsafe_allow_html=True)

    # 2. COMPARISON TABLE
    st.subheader("Detailed Comparison")
    
    comp_data = []
    for name, data in results_data.items():
        is_control = name == "Control"
        inc_rev = data["Revenue"] - base_rev
        profit = inc_rev - cost if not is_control else 0
        roi_val = (profit / cost * 100) if (not is_control and cost > 0) else 0
        
        comp_data.append({
            "Strategy": name,
            "Conv. Rate": f"{data['CR']*100:.2f}%",
            "Blended LTV": f"£{data['LTV']:.2f}",
            "Total Revenue": f"£{data['Revenue']:,.0f}",
            "Net Profit (vs Control)": f"£{profit:,.0f}" if not is_control else "-",
            "ROI": f"{roi_val:.0f}%" if not is_control else "-"
        })
        
    st.table(pd.DataFrame(comp_data))

    # 3. VISUALIZATION
    col_chart, col_be = st.columns([2, 1])
    
    with col_chart:
        st.subheader("Revenue Projection (2-Year)")
        chart_df = pd.DataFrame([{"Group": k, "Revenue": v["Revenue"]} for k,v in results_data.items()])
        fig = px.bar(chart_df, x="Group", y="Revenue", color="Group", text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
        
    with col_be:
        st.subheader("Break-Even Target")
        # Calc break even CR for the Cost
        # Revenue_New = Revenue_Old + Cost
        # Traffic * CR_New * LTV_New = Rev_Old + Cost
        # CR_New = (Rev_Old + Cost) / (Traffic * LTV_New)
        # Note: We use the *Variant's* LTV to calculate the target, because that's the mix we would be selling.
        
        target_cr = (base_rev + cost) / (traffic * results_data[best_variant]["LTV"])
        current_cr = results_data[best_variant]["CR"]
        
        st.metric(
            "Required Conv. Rate", 
            f"{target_cr*100:.2f}%",
            delta=f"{current_cr*100 - target_cr*100:.2f} pts vs actual",
            help=f"To pay back the £{cost} cost, {best_variant} must hit this conversion rate."
        )
        
        if current_cr >= target_cr:
            st.caption("✅ You are above the break-even point.")
        else:
            st.caption("❌ You are below the break-even point.")

else:
    st.warning("waiting for inputs...")
