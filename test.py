import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib 

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI Calculator", layout="wide", page_icon="💼")

# --- CUSTOM CSS FOR POLISH ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    /* Success/Error Boxes for Executive Summary */
    .success-box { padding: 20px; background-color: #d4edda; color: #155724; border-radius: 8px; border-left: 5px solid #28a745; margin-bottom: 20px; }
    .error-box { padding: 20px; background-color: #f8d7da; color: #721c24; border-radius: 8px; border-left: 5px solid #dc3545; margin-bottom: 20px; }
    .finance-mode { background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; color: #856404; }
    </style>
""", unsafe_allow_html=True)

# --- 1. HARDCODED PRICE BOOK ---
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
    # Promotions
    "Plumbing and Drainage Plus (Promo)": 6.00,
    "Plumbing and Electrics (Promo)": 42.00,
    "Landlord's Plumbing and Drainage Plus (Promo)": 6.00,
    "Landlord’s Plumbing and Electrics (Promo)": 66.00
}

# --- HELPER: FUZZY PARSING ---
def parse_paste_data(raw_text):
    parsed_rows = []
    if not raw_text: return pd.DataFrame()
    
    lines = raw_text.strip().split('\n')
    for line in lines:
        if '\t' in line: parts = line.split('\t')
        elif ',' in line: parts = line.split(',')
        else: parts = line.rsplit(' ', 1)

        if len(parts) >= 2:
            p_name = parts[0].strip()
            p_count_str = parts[1].strip().replace(',', '').replace('£', '')
            try: p_count = float(p_count_str)
            except: p_count = 0
            
            matched_price = 0
            status = "⚠️ Price Not Found"
            match_name = p_name

            if p_name in PRICE_CATALOG:
                matched_price = PRICE_CATALOG[p_name]
                status = "✅ Exact"
            else:
                found = False
                for cat_name, cat_price in PRICE_CATALOG.items():
                    if p_name.lower() == cat_name.lower():
                        matched_price = cat_price
                        match_name = cat_name
                        status = "✅ Exact (Case Fixed)"
                        found = True
                        break
                if not found:
                    matches = difflib.get_close_matches(p_name, PRICE_CATALOG.keys(), n=1, cutoff=0.6)
                    if matches:
                        match_name = matches[0]
                        matched_price = PRICE_CATALOG[match_name]
                        status = f"⚡ Fuzzy Match: {match_name}"
            
            parsed_rows.append({
                "Original Input": p_name, "Matched Policy": match_name,
                "Count": p_count, "Price": matched_price, "Status": status
            })
    return pd.DataFrame(parsed_rows)

# --- HELPER: LTV FACTOR CALCULATION ---
def calculate_ltv_factor(curve_df):
    cohort_size = 1.0
    cum_price_mult = 1.0
    total_factor = 0
    for _, row in curve_df.iterrows():
        year = row['Year']
        renewal = row['Renewal Rate (%)'] / 100.0
        price_idx = row['Price Index (%)'] / 100.0
        
        if year == 1:
            cohort_size, cum_price_mult = 1.0, 1.0
        else:
            cohort_size *= renewal
            cum_price_mult *= price_idx
        total_factor += (cohort_size * cum_price_mult)
    return total_factor

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### Evaluate the financial outcome of your A/B tests.")

with st.expander("📘 **New User Guide: How to use this tool**", expanded=True):
    st.markdown("""
    **Goal:** Determine if a new strategy (Variant) is profitable compared to the current strategy (Control).
    
    1.  **Define Scope (Sidebar):** Set the traffic volume, cost, and number of variants tested.
    2.  **Input Data (Tabs):** * Copy the **Product Name** and **Sales Count** columns from your Excel report.
        * Paste them into the text box for each tab (Control, Variant 1, etc.).
        * The tool handles pricing lookups and typo correction automatically.
    3.  **Read the Story:** Scroll down to the **Executive Summary** for a clear "Go / No-Go" recommendation.
    """)

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("⚙️ Simulation Settings")
    
    # FINANCE MODE
    st.markdown("---")
    finance_mode = st.toggle("🔐 Enable Finance Team Mode", value=False, 
                            help="Unlock advanced 5-year cohort modeling with variable retention and price indexing.")
    
    if finance_mode:
        st.markdown("<div class='finance-mode'><b>Finance Mode Active</b><br>Edit the LTV curve below.</div>", unsafe_allow_html=True)
        finance_defaults = {
            "Year": [1, 2, 3, 4, 5],
            "Renewal Rate (%)": [100, 80, 85, 90, 90], 
            "Price Index (%)": [100, 115, 105, 103, 103]
        }
        finance_curve = st.data_editor(
            pd.DataFrame(finance_defaults), hide_index=True,
            column_config={
                "Year": st.column_config.NumberColumn(format="%d"),
                "Renewal Rate (%)": st.column_config.NumberColumn(format="%d%%", help="% of users from prev year who renew"),
                "Price Index (%)": st.column_config.NumberColumn(format="%d%%", help="Price vs Prev Year (110% = 10% hike)")
            }
        )
        ltv_multiplier = calculate_ltv_factor(finance_curve)
    else:
        # SIMPLE MODE
        retention_simple = st.slider("Year 2 Renewal Rate", 50, 95, 80, format="%d%%", 
                                    help="Percentage of Year 1 customers who renew for Year 2.") / 100.0
        # Synthetic curve for backend compatibility
        finance_curve = pd.DataFrame({"Year": [1, 2], "Renewal Rate (%)": [100, retention_simple*100], "Price Index (%)": [100, 100]})
        ltv_multiplier = 1 + retention_simple

    st.markdown("---")
    
    # GLOBAL INPUTS
    num_variants = st.number_input("Number of Variants", min_value=1, max_value=5, value=1, 
                                  help="How many different test groups (excluding Control)?")
    variant_names = [f"Variant {i+1}" for i in range(num_variants)]
    
    traffic = st.number_input("Traffic per Group", value=10000, step=1000, 
                             help="Number of visitors/users in each test group.")
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500, 
                          help="Total one-time cost to build and launch this strategy.")

    st.divider()
    st.markdown("### 📚 Glossary")
    st.markdown("""
    * **LTV (Lifetime Value):** Total expected revenue from a customer over the defined horizon (2 or 5 years).
    * **Blended Price:** Average price weighted by the specific products sold in the test.
    * **Break-Even:** The conversion rate required to pay back the Implementation Cost.
    """)

# --- SECTION 1: DATA INPUT ---
st.header("1. Input Test Data")
st.caption(f"ℹ️ **Current Model:** {len(finance_curve)}-Year LTV Horizon. (Multiplier: {ltv_multiplier:.2f}x)")

tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])
results_data = {} 
all_groups = ["Control"] + variant_names

for i, group_name in enumerate(all_groups):
    with tabs[i]:
        col_input, col_check, col_metrics = st.columns([1.5, 2, 1])
        
        with col_input:
            st.markdown(f"**Paste {group_name} Mix** (Name | Count)")
            raw_paste = st.text_area(f"Input for {group_name}", height=200, key=f"paste_{group_name}", 
                                    placeholder="Plumbing...\t50\nGas Boiler\t20",
                                    help="Copy columns A (Name) and B (Count) from Excel and paste here.")
            
            cr_val = st.number_input(f"{group_name} Conversion Rate (%)", value=2.0 if i==0 else 2.2, 
                                    format="%.2f", key=f"cr_{group_name}",
                                    help=f"The final conversion rate achieved by {group_name}.") / 100

        df = parse_paste_data(raw_paste)
        
        if not df.empty:
            total_sales = df["Count"].sum()
            df["Mix %"] = df["Count"] / total_sales
            
            # Apply Finance Multiplier
            df["Item LTV"] = df["Price"] * ltv_multiplier
            
            blended_ltv = (df["Item LTV"] * df["Mix %"]).sum()
            avg_y1 = (df["Price"] * df["Mix %"]).sum()
            total_revenue = traffic * cr_val * blended_ltv
            
            results_data[group_name] = {
                "CR": cr_val, "LTV": blended_ltv, "Revenue": total_revenue, "AvgPrice": avg_y1
            }

            with col_check:
                st.markdown("**Data Validation**")
                st.dataframe(df[["Matched Policy", "Count", "Price", "Status"]], 
                             column_config={"Price": st.column_config.NumberColumn(format="£%.2f")},
                             hide_index=True, height=200, use_container_width=True)

            with col_metrics:
                st.markdown("**Group Performance**")
                st.metric("Blended LTV", f"£{blended_ltv:.2f}", help="Avg revenue per customer over full horizon")
                st.metric("Proj. Revenue", f"£{total_revenue:,.0f}", help="Traffic x CR x LTV")
        else:
            with col_check: st.info(f"👈 Waiting for data for {group_name}...")

# --- SECTION 2: EXECUTIVE SUMMARY ---
if "Control" in results_data and len(results_data) > 1:
    st.divider()
    st.header("2. Executive Summary & Recommendation")
    
    # Logic
    best_variant = max(results_data, key=lambda x: results_data[x]['Revenue'] if x != 'Control' else -1)
    base_rev = results_data["Control"]["Revenue"]
    best_rev = results_data[best_variant]["Revenue"]
    incremental_rev = best_rev - base_rev
    net_profit = incremental_rev - cost
    roi = (net_profit / cost) * 100 if cost > 0 else 0
    
    # 1. RECOMMENDATION BOX
    if net_profit > 0:
        st.markdown(f"""
        <div class="success-box">
            <h3 style="margin:0">🚀 Recommendation: Roll Out {best_variant}</h3>
            <p style="margin:5px 0 0 0">
                The data supports switching to <b>{best_variant}</b>. 
                It is projected to generate <b>£{net_profit:,.0f}</b> in pure profit (after costs) with an ROI of <b>{roi:.0f}%</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
         st.markdown(f"""
        <div class="error-box">
            <h3 style="margin:0">🛑 Recommendation: Do Not Roll Out</h3>
            <p style="margin:5px 0 0 0">
                <b>{best_variant}</b> is not financially viable. 
                Despite any conversion lift, the projected revenue does not cover the £{cost:,.0f} implementation cost. 
                Rolling this out would result in a loss of <b>£{abs(net_profit):,.0f}</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 2. COMPARISON TABLE
    st.subheader("Detailed Financial Breakdown")
    comp_data = []
    for name, data in results_data.items():
        is_ctrl = name == "Control"
        inc = data["Revenue"] - base_rev
        prof = inc - cost if not is_ctrl else 0
        roi_v = (prof/cost * 100) if (not is_ctrl and cost > 0) else 0
        
        comp_data.append({
            "Strategy": name,
            "Conv. Rate": f"{data['CR']*100:.2f}%",
            "Blended LTV": f"£{data['LTV']:.2f}",
            "Total Revenue": f"£{data['Revenue']:,.0f}",
            "Net Profit": f"£{prof:,.0f}" if not is_ctrl else "-",
            "ROI": f"{roi_v:.0f}%" if not is_ctrl else "-"
        })
    st.table(pd.DataFrame(comp_data))

    # 3. CHARTS
    c1, c2 = st.columns([2, 1])
    with c1:
        df_chart = pd.DataFrame([{"Group": k, "Revenue": v["Revenue"]} for k,v in results_data.items()])
        fig = px.bar(df_chart, x="Group", y="Revenue", color="Group", title="Total Projected Revenue", text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        # Break Even
        target_cr = (base_rev + cost) / (traffic * results_data[best_variant]["LTV"])
        curr_cr = results_data[best_variant]["CR"]
        st.metric("Break-Even Target", f"{target_cr*100:.2f}%", 
                  delta=f"{curr_cr*100 - target_cr*100:.2f} pts vs Actual",
                  help=f"{best_variant} must hit this conversion rate to pay back the £{cost} cost.")
        if curr_cr < target_cr:
            st.caption("❌ Below Break-Even")
        else:
            st.caption("✅ Above Break-Even")

    # --- SECTION 3: RISK SIMULATOR ---
    st.divider()
    st.header("3. 🎲 Risk & Confidence Analysis")
    st.markdown(f"**Question:** How likely is {best_variant} to actually make money if our estimates are slightly off?")
    
    if st.button("Run 1,000 Simulations"):
        with st.spinner("Simulating Futures..."):
            sims = 1000
            volatility = 0.10 
            
            # Variant Inputs
            v_cr = results_data[best_variant]["CR"]
            v_ltv = results_data[best_variant]["LTV"]
            v_price = results_data[best_variant]["AvgPrice"]
            
            # Control Inputs
            c_cr = results_data["Control"]["CR"]
            c_ltv = results_data["Control"]["LTV"]
            c_price = results_data["Control"]["AvgPrice"]
            
            # Randomize CR
            sim_v_cr = np.random.normal(v_cr, v_cr * volatility, sims)
            sim_c_cr = np.random.normal(c_cr, c_cr * (volatility*0.5), sims) # Control is more stable
            
            # Randomize Retention (Affects LTV Multiplier)
            # We approximate this by fluctuating the LTV value directly relative to base price
            sim_mult_impact = np.random.normal(1.0, 0.05, sims) # +/- 5% impact on LTV curve
            
            sim_v_ltv = v_ltv * sim_mult_impact
            sim_c_ltv = c_ltv * sim_mult_impact
            
            # Calc Profits
            sim_profit = (traffic * sim_v_cr * sim_v_ltv) - (traffic * sim_c_cr * sim_c_ltv) - cost
            
            # Results
            wins = np.sum(sim_profit > 0)
            win_rate = (wins/sims)*100
            
            r1, r2 = st.columns([1, 2])
            with r1:
                st.metric("Probability of Profit", f"{win_rate:.1f}%")
                if win_rate > 80: st.success("Low Risk")
                elif win_rate > 50: st.warning("Moderate Risk")
                else: st.error("High Risk")
                st.write(f"**Worst Case:** £{np.percentile(sim_profit, 5):,.0f}")
                st.write(f"**Best Case:** £{np.percentile(sim_profit, 95):,.0f}")
            with r2:
                fig = px.histogram(x=sim_profit, nbins=40, title=f"Profit Distribution ({best_variant})", color_discrete_sequence=['#00CC96'])
                fig.add_vline(x=0, line_dash="dash", line_color="red")
                fig.update_layout(xaxis_title="Net Profit (£)", showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 **Action Required:** Paste your product mix in the Control and Variant tabs to see the analysis.")
