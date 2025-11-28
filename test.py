import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib 

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI Calculator", layout="wide", page_icon="💼")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    .success-box { padding: 15px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px; }
    .error-box { padding: 15px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 10px; }
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
            
            # MATCHING LOGIC
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

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### Evaluate the financial impact of A/B tests across multiple variants.")

with st.expander("📘 **Start Here: How to use this tool**", expanded=True):
    st.markdown("""
    **Who is this for?** Executives and Strategy Leads.
    
    1.  **Define Variants (Sidebar):** Select how many test groups you had (e.g., Control + Variant 1).
    2.  **Paste Data (Tabs):** For each tab, copy the product mix (Name | Count) from Excel and paste it in.
    3.  **Check Results:** We automatically calculate the ROI, Break-Even point, and Risk Profile below.
    """)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Global Settings")
    num_variants = st.number_input("Number of New Variants", min_value=1, max_value=5, value=1)
    variant_names = [f"Variant {i+1}" for i in range(num_variants)]
    
    st.divider()
    st.subheader("Market Assumptions")
    traffic = st.number_input("Traffic per Variant", value=10000, step=1000)
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500)
    retention = st.slider("Year 2 Renewal Rate", 50, 95, 80, format="%d%%") / 100.0

    st.divider()
    st.markdown("### 📚 Glossary")
    st.markdown("""
    * **LTV:** Lifetime Value (2 Years).
    * **Blended Price:** Average price weighted by product mix.
    * **Monte Carlo:** A risk simulation to test 'what-if' scenarios.
    """)

# --- SECTION 1: INPUTS ---
st.header("1. Input Test Data")
st.info("Paste your Excel data below. We automatically clean typos and look up prices.")

tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])
results_data = {} 

all_groups = ["Control"] + variant_names

for i, group_name in enumerate(all_groups):
    with tabs[i]:
        col_input, col_check, col_metrics = st.columns([1.5, 2, 1])
        
        with col_input:
            st.markdown(f"**Paste {group_name} Mix** (Name | Count)")
            raw_paste = st.text_area(f"Input for {group_name}", height=200, key=f"paste_{group_name}", 
                                    placeholder="Plumbing...\t50\nGas Boiler\t20")
            
            cr_val = st.number_input(f"{group_name} Conversion Rate (%)", value=2.0 if i==0 else 2.2, 
                                    format="%.2f", key=f"cr_{group_name}") / 100

        df = parse_paste_data(raw_paste)
        
        if not df.empty:
            total_sales = df["Count"].sum()
            df["Mix %"] = df["Count"] / total_sales
            # LTV = Y1 + (Y1 * Retention) assuming Y2 price is same
            df["Item LTV"] = df["Price"] + (df["Price"] * retention)
            
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
                st.metric("Blended LTV", f"£{blended_ltv:.2f}")
                st.metric("Proj. Revenue", f"£{total_revenue:,.0f}")
        else:
            with col_check: st.info(f"👈 Waiting for data for {group_name}...")

# --- SECTION 2: EXECUTIVE SUMMARY ---
if "Control" in results_data and len(results_data) > 1:
    st.divider()
    st.header("2. Executive Summary & Recommendation")
    
    # Identify Winner
    best_variant = max(results_data, key=lambda x: results_data[x]['Revenue'] if x != 'Control' else -1)
    
    base_rev = results_data["Control"]["Revenue"]
    best_rev = results_data[best_variant]["Revenue"]
    incremental = best_rev - base_rev
    net_profit = incremental - cost
    roi = (net_profit / cost) * 100 if cost > 0 else 0
    
    # 1. NARRATIVE
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
        target_cr = (base_rev + cost) / (traffic * results_data[best_variant]["LTV"])
        current_cr = results_data[best_variant]["CR"]
        
        st.metric("Required Conv. Rate", f"{target_cr*100:.2f}%",
            delta=f"{current_cr*100 - target_cr*100:.2f} pts vs actual",
            help=f"To pay back the £{cost} cost, {best_variant} must hit this rate.")

    # --- SECTION 3: RISK SIMULATOR (RESTORED) ---
    st.divider()
    st.header("3. 🎲 Risk & Confidence Simulator")
    st.markdown(f"""
    **Context:** We are simulating **1,000 futures** comparing **{best_variant}** vs **Control**. 
    We slightly vary the Conversion Rate and Retention in every scenario to see how safe this bet is.
    """)
    
    if st.button("Run Risk Analysis"):
        with st.spinner("Running Monte Carlo Simulation..."):
            sims = 1000
            volatility = 0.10 # 10% standard deviation
            
            # Best Variant Sim Inputs
            var_cr = results_data[best_variant]["CR"]
            var_ltv_base = results_data[best_variant]["LTV"]
            # We approximate LTV volatility by perturbing retention
            var_price = results_data[best_variant]["AvgPrice"] 
            
            # Control Sim Inputs
            ctrl_cr = results_data["Control"]["CR"]
            ctrl_ltv = results_data["Control"]["LTV"]
            
            # --- ARRAYS ---
            # 1. Randomized Conversion Rates
            sim_cr_var = np.random.normal(var_cr, var_cr * volatility, sims)
            sim_cr_ctrl = np.random.normal(ctrl_cr, ctrl_cr * (volatility/2), sims) # Control is usually more stable
            
            # 2. Randomized Retention (Impacts LTV)
            sim_retention = np.random.normal(retention, retention * 0.05, sims)
            sim_retention = np.clip(sim_retention, 0.1, 1.0)
            
            # Reconstruct LTV based on randomized retention
            # LTV = Price + (Price * SimRetention)
            sim_ltv_var = var_price + (var_price * sim_retention)
            # For simplicity, we assume Control LTV fluctuates similarly or stays static. Let's fluctuate it.
            # We need Control Avg Price
            ctrl_price = results_data["Control"]["AvgPrice"]
            sim_ltv_ctrl = ctrl_price + (ctrl_price * sim_retention)
            
            # 3. Calculate Profit Arrays
            sim_rev_var = traffic * sim_cr_var * sim_ltv_var
            sim_rev_ctrl = traffic * sim_cr_ctrl * sim_ltv_ctrl
            
            sim_net_profit = (sim_rev_var - sim_rev_ctrl) - cost
            
            # 4. Metrics
            wins = np.sum(sim_net_profit > 0)
            win_rate = (wins / sims) * 100
            
            r1, r2 = st.columns([1, 2])
            with r1:
                st.markdown(f"### Probability of Profit: :blue[{win_rate:.1f}%]")
                if win_rate > 80: st.success("Outcome: Low Risk Strategy")
                elif win_rate > 50: st.warning("Outcome: Moderate Risk")
                else: st.error("Outcome: High Risk / Gamble")
                
                st.write(f"**Best Case (95th %):** £{np.percentile(sim_net_profit, 95):,.0f}")
                st.write(f"**Worst Case (5th %):** £{np.percentile(sim_net_profit, 5):,.0f}")
            
            with r2:
                fig = px.histogram(x=sim_net_profit, nbins=40, title=f"Profit Distribution ({best_variant})", color_discrete_sequence=['#00CC96'])
                fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Break Even")
                fig.update_layout(xaxis_title="Net Profit (£)", showlegend=False, height=350)
                st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Please input data for Control and at least one Variant.")
