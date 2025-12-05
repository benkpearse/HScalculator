import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib 
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Enterprise ROI & LTV Modeler", layout="wide", page_icon="📈")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    
    /* Section Headers */
    .section-header { font-size: 1.1rem; font-weight: 700; color: #333; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
    .sub-text { font-size: 0.85rem; color: #666; margin-bottom: 10px; font-style: italic; }
    
    /* Mode Badges */
    .mode-badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 0.85em; display: inline-block; margin-bottom: 10px;}
    .marketing-mode { background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
    .finance-mode { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    
    /* Result Boxes */
    .success-box { padding: 20px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 20px; border-radius: 4px; color: #155724; }
    .error-box { padding: 20px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 20px; border-radius: 4px; color: #721c24; }
    .warning-box { padding: 15px; background-color: #fff3cd; border-left: 5px solid #ffc107; margin-bottom: 15px; border-radius: 4px; color: #856404; }
    </style>
""", unsafe_allow_html=True)

# --- 1. CONFIGURATION DATA ---

# Hardcoded Price Book
PRICE_CATALOG = {
    "Plumbing and Drainage Plus": 12.00, "Plumbing and Electrics": 48.00,
    "Heating, Plumbing and Electrics Plus": 216.00, "Heating, Plumbing and Electrics": 192.00,
    "Heating and Plumbing": 174.00, "Gas Boiler and Central Heating": 162.00,
    "Electrics": 36.00, "Gas Boiler": 108.00, "Gas Boiler service": 108.00,
    "Gas Boiler Service": 108.00, "Gas Boiler Service and Gas Safety Certificate": 108.00,
    "Heating System and Electrics": 192.00, "Heating and Electrics": 192.00,
    "Landlord's Plumbing and Drainage Plus": 12.00, "Landlord’s Electrics": 60.00,
    "Landlord's Plumbing and Electrics": 72.00, "Landlord’s Gas Boiler": 132.00,
    "Landlord’s Gas Boiler and Central Heating": 198.00, "Landlord’s Heating and Plumbing": 210.00,
    "Landlord’s Heating, Plumbing and Electrics": 246.00, "Landlord’s Heating, Plumbing and Electrics Plus": 270.00,
    "Landlord’s Gas Safety Certificate": 108.00,
    "Plumbing and Drainage Plus (Promo)": 6.00, "Plumbing and Electrics (Promo)": 42.00,
    "Landlord's Plumbing and Drainage Plus (Promo)": 6.00, "Landlord’s Plumbing and Electrics (Promo)": 66.00
}

# Seasonality Data (From User Input)
SEASONALITY_INDICES = {
    "Jan": 1.48, "Feb": 1.46, "Mar": 1.72, "Apr": 0.52, "May": 0.70, "Jun": 0.59,
    "Jul": 0.59, "Aug": 0.80, "Sep": 0.73, "Oct": 1.21, "Nov": 1.46, "Dec": 0.75
}
MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# --- HELPER FUNCTIONS ---
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
                matches = difflib.get_close_matches(p_name, PRICE_CATALOG.keys(), n=1, cutoff=0.6)
                if matches:
                    match_name = matches[0]
                    matched_price = PRICE_CATALOG[match_name]
                    status = f"⚡ Fuzzy: {match_name}"
            
            parsed_rows.append({
                "Original Input": p_name, "Matched Policy": match_name,
                "Count": p_count, "Base Price": matched_price, "Status": status
            })
    return pd.DataFrame(parsed_rows)

def get_seasonality_multiplier(start_month_idx, current_month_offset):
    # Calculate which calendar month we are in (0=Jan, 11=Dec)
    target_idx = (start_month_idx + current_month_offset) % 12
    month_name = MONTH_ORDER[target_idx]
    return SEASONALITY_INDICES.get(month_name, 1.0)

# --- HEADER ---
st.title("💼 Enterprise ROI & LTV Modeler")
st.markdown("### Financial Projection with Seasonality & Decay")

with st.expander("📘 **Guide & Glossary: Start Here**", expanded=True):
    st.markdown("""
    **1. Test Context (Past):** Enter your A/B test data to calculate the Conversion Rate lift.
    **2. Rollout Scope (Future):** Enter the expected traffic. We apply **Seasonality** (Heating peaks in Winter) to project accurate cash flow.
    **3. Waterfalls & Risk:** The output shows a financial bridge of where value is created vs. lost to decay/costs.
    
    **Key Terms:**
    * **Seasonality Index:** Multiplier for traffic/sales based on the month (e.g., Mar = 1.72x average).
    * **Decay Rate:** How fast the "lift" from the A/B test fades due to the novelty effect wearing off.
    * **NPV:** Net Present Value. Future cash is discounted (worth less than today's cash).
    """)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # STEP 1
    st.markdown("<div class='section-header'>1. LTV Engine</div>", unsafe_allow_html=True)
    mode_selection = st.radio("Mode:", ["Marketing Mode (2-Year)", "Finance Mode (5-Year NPV)"], 
                             label_visibility="collapsed",
                             help="Marketing: Simple 2-year sum.\nFinance: 5-year view.")
    is_finance = "Finance" in mode_selection
    
    # STEP 2
    st.markdown("<div class='section-header'>2. Test Context (Past)</div>", unsafe_allow_html=True)
    test_days = st.number_input("Test Duration (Days)", value=14, step=1, help="Duration of the A/B test.")
    test_visitors_total = st.number_input("Total Test Visitors", value=40000, step=1000, 
                                         help="Total unique visitors across ALL groups. Crucial for accurate Conversion Rate calculation.")
    num_variants = st.number_input("Number of Variants", 1, 5, 1)

    # STEP 3
    st.markdown("<div class='section-header'>3. Rollout Scope (Future)</div>", unsafe_allow_html=True)
    traffic_monthly = st.number_input("Base Monthly Traffic", value=10000, step=1000, 
                                     help="The 'Average' month traffic. Seasonality will multiply this up or down.")
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500, help="One-off cost to build the winning feature.")

    # STEP 4
    st.markdown("<div class='section-header'>4. Market Dynamics</div>", unsafe_allow_html=True)
    
    # Seasonality Controls
    use_seasonality = st.checkbox("Apply Seasonality?", value=True, help="Apply the specific seasonal curve.")
    if use_seasonality:
        launch_month = st.selectbox("Launch Month", MONTH_ORDER, index=0, 
                                   help="Which month does the 24-month projection start? (Affects the shape of the curve).")
        launch_month_idx = MONTH_ORDER.index(launch_month)
    else:
        launch_month_idx = 0
    
    decay_rate = st.slider("Monthly Lift Decay", 0, 20, 5, format="%d%%", 
                          help="Performance drop-off per month (Novelty Effect). 5% means the lift shrinks by 5% monthly.") / 100.0
    
    if is_finance:
        discount_rate = st.slider("Discount Rate (WACC)", 0, 15, 5, format="%d%%", help="Used for NPV calculation.") / 100.0
    else:
        global_retention = st.slider("Year 2 Retention", 50, 95, 80, format="%d%%", help="% of users renewing for Year 2.") / 100.0

# --- MAIN CONTENT ---

if test_visitors_total == 0 or traffic_monthly == 0:
    st.error("⚠️ Traffic cannot be zero. Update Sidebar.")
    st.stop()

# --- ENGINE LOGIC ---
product_ltv_map = {} 

st.header("1. Assumptions Engine")

if is_finance:
    st.markdown("<div class='mode-badge finance-mode'>🔓 FINANCE ENGINE: 5-Year NPV Model</div>", unsafe_allow_html=True)
    with st.expander("📊 **Edit Finance Matrix**", expanded=False):
        st.caption("Detailed 5-Year cash flow settings per product.")
        rows = []
        for p_name, p_price in PRICE_CATALOG.items():
            rows.append({
                "Product": p_name, "Y1 Price": p_price,
                "Ret Y1->Y2 (%)": 80, "Price Y2 (£)": p_price * 1.05,
                "Ret Y2->Y3 (%)": 85, "Price Y3 (£)": p_price * 1.10,
                "Ret Y3->Y4 (%)": 90, "Price Y4 (£)": p_price * 1.15,
                "Ret Y4->Y5 (%)": 90, "Price Y5 (£)": p_price * 1.20,
            })
        matrix_df = st.data_editor(pd.DataFrame(rows), hide_index=True, height=250, use_container_width=True)
        
        for idx, row in matrix_df.iterrows():
            cash_flows = [row["Y1 Price"]]
            cohort = 1.0
            for year_idx in range(2, 6):
                ret_col = f"Ret Y{year_idx-1}->Y{year_idx} (%)"
                price_col = f"Price Y{year_idx} (£)"
                cohort *= (row[ret_col]/100)
                cash_flows.append(cohort * row[price_col])
            npv_manual = sum([cf / ((1+discount_rate)**t) for t, cf in enumerate(cash_flows)])
            product_ltv_map[row["Product"]] = npv_manual
else:
    st.markdown("<div class='mode-badge marketing-mode'>🚀 MARKETING ENGINE: 2-Year Simple Model</div>", unsafe_allow_html=True)
    st.caption("Calculating: Year 1 Price + (Year 2 Price * Global Retention).")
    for p_name, p_price in PRICE_CATALOG.items():
        product_ltv_map[p_name] = p_price + (p_price * global_retention)

# --- INPUT SECTION ---
st.divider()
st.header("2. Input Test Results")
st.info("👇 **Action:** Paste Excel Sales Data (Name | Count) for each group.")

variant_names = [f"Variant {i+1}" for i in range(num_variants)]
tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])

group_inputs = {}
visitors_per_group_est = test_visitors_total / (num_variants + 1)

for i, group in enumerate(["Control"] + variant_names):
    with tabs[i]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**{group} Sales**")
            raw = st.text_area(f"Paste {group}", height=120, key=f"p_{group}", placeholder="Name\tCount", label_visibility="collapsed")
            
        df = parse_paste_data(raw)
        
        if not df.empty:
            total_sales = df["Count"].sum()
            calculated_cr = total_sales / visitors_per_group_est
            
            with c1:
                if calculated_cr > 0.08:
                    st.markdown(f"<div class='warning-box'>⚠️ <b>High CR ({calculated_cr*100:.1f}%)</b><br>Check Total Visitors in sidebar.</div>", unsafe_allow_html=True)
                
                st.metric("Conversion Rate", f"{calculated_cr*100:.2f}%", help=f"Sales ({int(total_sales)}) / Visitors ({int(visitors_per_group_est)})")

            df["Unit Value (£)"] = df["Matched Policy"].map(product_ltv_map).fillna(0)
            df["Mix"] = df["Count"] / total_sales
            blended_val = (df["Unit Value (£)"] * df["Mix"]).sum()
            
            group_inputs[group] = {
                "CR_Initial": calculated_cr,
                "LTV_Per_User": blended_val,
                "Mix_Table": df
            }
            
            with c2:
                st.dataframe(df[["Matched Policy", "Count", "Unit Value (£)"]], height=150, use_container_width=True, hide_index=True)
                st.caption(f"**Avg LTV:** £{blended_val:.2f}")

# --- PROJECTION ENGINE ---
st.divider()
st.header("3. Executive Summary (24 Month Rollout)")

if "Control" in group_inputs and len(group_inputs) > 1:
    
    calc_results = []
    months = 24
    control_data = group_inputs["Control"]
    
    # Calculate Control Stream (With Seasonality, No Decay)
    control_rev_stream = []
    for m in range(months):
        seasonality = get_seasonality_multiplier(launch_month_idx, m) if use_seasonality else 1.0
        # Revenue = BaseTraffic * Seasonality * ControlCR * ControlLTV
        rev = (traffic_monthly * seasonality) * control_data["CR_Initial"] * control_data["LTV_Per_User"]
        control_rev_stream.append(rev)
    
    control_total_rev = sum(control_rev_stream)

    for name, data in group_inputs.items():
        if name == "Control":
            calc_results.append({
                "Group": name, "Total Rev": control_total_rev, "Net Profit": 0, "ROI": 0,
                "Revenue_Stream": control_rev_stream
            })
            continue
            
        # Variant Stream (With Seasonality AND Decay)
        initial_lift = data["CR_Initial"] - control_data["CR_Initial"]
        variant_rev_stream = []
        
        for m in range(months):
            seasonality = get_seasonality_multiplier(launch_month_idx, m) if use_seasonality else 1.0
            
            # Apply Decay to Lift
            decayed_lift = initial_lift * ((1 - decay_rate) ** m)
            current_cr = max(control_data["CR_Initial"], control_data["CR_Initial"] + decayed_lift)
            
            # Calculate Revenue
            rev = (traffic_monthly * seasonality) * current_cr * data["LTV_Per_User"]
            variant_rev_stream.append(rev)
            
        variant_total_rev = sum(variant_rev_stream)
        incremental = variant_total_rev - control_total_rev
        profit = incremental - cost
        roi = (profit/cost)*100 if cost > 0 else 0
        
        calc_results.append({
            "Group": name,
            "Total Rev": variant_total_rev,
            "Net Profit": profit,
            "ROI": roi,
            "Revenue_Stream": variant_rev_stream
        })

    best_res = max([x for x in calc_results if x["Group"] != "Control"], key=lambda x: x["Net Profit"])
    
    # --- WATERFALL CHART ---
    st.subheader("Financial Bridge (24 Months)")
    st.caption("Visualizing the components of profitability.")
    
    # Waterfall Logic
    wf_base = control_total_rev
    wf_lift = best_res["Total Rev"] - control_total_rev # Gross Incremental
    wf_cost = -cost
    wf_net = wf_lift + wf_cost
    
    fig_wf = go.Figure(go.Waterfall(
        name = "24-Month Bridge", orientation = "v",
        measure = ["absolute", "relative", "relative", "total"],
        x = ["Baseline Revenue", "Incremental Lift", "Implementation Cost", "Net Profit"],
        textposition = "outside",
        text = [f"£{wf_base/1e6:.2f}M", f"+£{wf_lift/1e3:.0f}k", f"-£{abs(wf_cost)/1e3:.0f}k", f"£{wf_net/1e3:.0f}k"],
        y = [wf_base, wf_lift, wf_cost, 0], 
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        decreasing = {"marker":{"color":"#EF553B"}},
        increasing = {"marker":{"color":"#00CC96"}},
        totals = {"marker":{"color":"#636efa"}}
    ))
    fig_wf.update_layout(title=f"Profit Bridge: {best_res['Group']}", waterfallgap = 0.3)
    
    c1, c2 = st.columns([2, 1])
    with c1:
        st.plotly_chart(fig_wf, use_container_width=True)
        
    with c2:
        st.markdown(f"""
        <div class='success-box' style='height: 100%;'>
            <h3 style='margin-top:0'>Recommendation</h3>
            <p><b>Strategy:</b> {best_res['Group']}</p>
            <p><b>Outcome:</b> £{best_res['Net Profit']:,.0f} Profit</p>
            <p><b>ROI:</b> {best_res['ROI']:.0f}%</p>
            <hr>
            <small>Includes Seasonality & {decay_rate*100:.0f}% monthly decay.</small>
        </div>
        """, unsafe_allow_html=True)

    # --- REVENUE LINE CHART ---
    st.subheader("Projected Cash Flow")
    st.caption("Visualizing Seasonality and Decay over 24 months. Hover to see the calendar month.")
    
    chart_df = pd.DataFrame()
    chart_df["Month"] = list(range(1, 25))
    
    # Add Month Labels (e.g. Jan, Feb) for clarity
    month_labels = [MONTH_ORDER[(launch_month_idx + m) % 12] for m in range(24)]
    chart_df["Label"] = month_labels
    
    chart_df["Control"] = calc_results[0]["Revenue_Stream"]
    for res in calc_results:
        if res["Group"] != "Control":
            chart_df[res["Group"]] = res["Revenue_Stream"]
            
    fig_line = px.line(chart_df, x="Month", y=chart_df.columns[2:], # Skip Month and Label cols
                 labels={"value": "Revenue (£)", "variable": "Strategy"},
                 hover_data={"Label": True})
    
    st.plotly_chart(fig_line, use_container_width=True)

    # --- RISK SIMULATOR ---
    st.divider()
    st.header("4. Confidence Check (Risk Simulator)")
    
    if st.button("Run Simulation", type="primary"):
        with st.spinner("Simulating..."):
            sims = 1000
            volatility = 0.10
            
            v_rev = best_res["Total Rev"]
            c_rev = control_total_rev
            
            sim_v_rev = np.random.normal(v_rev, v_rev * volatility, sims)
            sim_c_rev = np.random.normal(c_rev, c_rev * (volatility * 0.5), sims)
            
            sim_profit = (sim_v_rev - sim_c_rev) - cost
            win_rate = (np.sum(sim_profit > 0) / sims) * 100
            
            r1, r2 = st.columns([1, 2])
            with r1:
                st.metric("Probability of Profit", f"{win_rate:.1f}%")
                if win_rate > 80: st.success("Low Risk")
                elif win_rate > 50: st.warning("Moderate Risk")
                else: st.error("High Risk")
                st.write(f"**Worst Case (5%):** £{np.percentile(sim_profit, 5):,.0f}")
                
            with r2:
                fig_risk = px.histogram(x=sim_profit, nbins=40, title="Profit Distribution", color_discrete_sequence=['#00CC96'])
                fig_risk.add_vline(x=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_risk, use_container_width=True)

else:
    st.info("Please input data in the tabs above.")
