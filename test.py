import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib 

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI & LTV Calculator", layout="wide", page_icon="📈")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    
    /* Section Headers */
    .section-header { font-size: 1.1rem; font-weight: 700; color: #333; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #ddd; padding-bottom: 5px; }
    .sub-text { font-size: 0.9rem; color: #666; margin-bottom: 15px; }
    
    /* Mode Badges */
    .mode-badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 0.85em; display: inline-block; margin-bottom: 10px;}
    .marketing-mode { background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
    .finance-mode { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    
    /* Result Boxes */
    .success-box { padding: 20px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 20px; border-radius: 4px; color: #155724; }
    .error-box { padding: 20px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 20px; border-radius: 4px; color: #721c24; }
    </style>
""", unsafe_allow_html=True)

# --- 1. HARDCODED PRICE BOOK ---
PRICE_CATALOG = {
    "Plumbing and Drainage Plus": 12.00,
    "Plumbing and Electrics": 48.00,
    "Heating, Plumbing and Electrics Plus": 216.00,
    "Heating, Plumbing and Electrics": 192.00,
    "Heating and Plumbing": 174.00,
    "Gas Boiler and Central Heating": 162.00,
    "Electrics": 36.00,
    "Gas Boiler": 108.00,
    "Gas Boiler service": 108.00,
    "Landlord's Plumbing and Drainage Plus": 12.00,
    "Landlord’s Electrics": 60.00,
    "Landlord's Plumbing and Electrics": 72.00,
    "Landlord’s Gas Boiler": 132.00,
    "Landlord’s Gas Boiler and Central Heating": 198.00,
    "Landlord’s Heating and Plumbing": 210.00,
    "Landlord’s Heating, Plumbing and Electrics": 246.00,
    "Landlord’s Heating, Plumbing and Electrics Plus": 270.00,
    "Landlord’s Gas Safety Certificate": 108.00,
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

# --- HEADER ---
st.title("💼 Strategic ROI & LTV Calculator")
st.markdown("### Evaluate A/B Tests with Financial Precision")

with st.expander("📘 **Guide: Test Data vs. Rollout Projection**", expanded=True):
    st.markdown("""
    To get accurate numbers, we separate **The Past (Test)** from **The Future (Rollout)**.
    
    1.  **Test Context (Sidebar Step 2):** Input the actual duration and total visitors of your A/B test. This calculates your *true* Conversion Rate.
    2.  **Rollout Context (Sidebar Step 3):** Input the expected monthly traffic if you launch this feature. This scales the revenue.
    3.  **LTV Engine (Sidebar Step 1):** 'Marketing Mode' projects 2 years. 'Finance Mode' projects 5 years (NPV).
    """)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # --- STEP 1: ENGINE ---
    st.markdown("<div class='section-header'>1. LTV Engine</div>", unsafe_allow_html=True)
    mode_selection = st.radio("Calculation Mode:", 
                             ["Marketing Mode (2-Year)", "Finance Mode (5-Year NPV)"],
                             help="Defines how we calculate the long-term value of a single customer.")
    is_finance = "Finance" in mode_selection
    
    # --- STEP 2: TEST CONTEXT ---
    st.markdown("<div class='section-header'>2. Test Context (The Past)</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>Used to calculate conversion rates.</div>", unsafe_allow_html=True)
    
    test_days = st.number_input("Test Duration (Days)", value=14, step=1, 
                               help="How many days did the A/B test run?")
    
    test_visitors_total = st.number_input("Total Test Visitors", value=5000, step=100,
                                         help="Total unique visitors across ALL groups during the test period.")
    
    num_variants = st.number_input("Number of Variants", 1, 5, 1, 
                                  help="Excluding Control, how many new versions?")

    # --- STEP 3: ROLLOUT PROJECTION ---
    st.markdown("<div class='section-header'>3. Rollout Scope (The Future)</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-text'>Used to project future revenue.</div>", unsafe_allow_html=True)
    
    traffic_monthly = st.number_input("Expected Monthly Traffic", value=10000, step=1000, 
                                     help="If we roll this out, how many visitors per month will see it?")
    
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500, 
                          help="One-time cost to build/launch.")

    # --- STEP 4: DYNAMICS ---
    st.markdown("<div class='section-header'>4. Dynamics</div>", unsafe_allow_html=True)
    
    decay_rate = st.slider("Monthly Lift Decay", 0, 20, 5, format="%d%%",
                          help="Performance drop-off per month (Novelty Effect).") / 100.0
    
    if is_finance:
        st.caption("Finance: Discount Rate (WACC)")
        discount_rate = st.slider("Discount Rate", 0, 15, 5, format="%d%%") / 100.0
    else:
        st.caption("Marketing: Retention")
        global_retention = st.slider("Year 2 Retention", 50, 95, 80, format="%d%%") / 100.0

# --- MAIN CONTENT ---

# --- VALIDATION ---
if test_visitors_total == 0 or traffic_monthly == 0:
    st.error("⚠️ Traffic cannot be zero. Please update the Sidebar.")
    st.stop()

# --- ENGINE LOGIC ---
product_ltv_map = {} 

st.header("1. Financial Assumptions")

if is_finance:
    st.markdown("<div class='mode-badge finance-mode'>🔓 FINANCE ENGINE: 5-Year NPV Model</div>", unsafe_allow_html=True)
    with st.expander("📊 **Edit Finance Matrix**", expanded=False):
        # Build Grid
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
        
        # CALC NPV
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
    for p_name, p_price in PRICE_CATALOG.items():
        product_ltv_map[p_name] = p_price + (p_price * global_retention)

# --- INPUT SECTION ---
st.divider()
st.header("2. Input Test Results")
st.info("👇 **Action:** Paste the Excel Sales Data (Name | Count) for the duration of the test.")

variant_names = [f"Variant {i+1}" for i in range(num_variants)]
tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])

group_inputs = {}

# We estimate visitors per group assuming equal split for simplicity
visitors_per_group_est = test_visitors_total / (num_variants + 1)

for i, group in enumerate(["Control"] + variant_names):
    with tabs[i]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**{group} Sales Data**")
            raw = st.text_area(f"Paste {group}", height=120, key=f"p_{group}", 
                              placeholder="Plumbing...\t50\nGas Boiler\t20", label_visibility="collapsed")
            
        df = parse_paste_data(raw)
        
        if not df.empty:
            total_sales = df["Count"].sum()
            
            # CALCULATE CR based on Inputs
            # CR = Sales / Visitors in this group
            calculated_cr = total_sales / visitors_per_group_est
            
            with c1:
                st.metric(f"Sales Count ({test_days} Days)", f"{int(total_sales)}")
                st.metric("Conversion Rate (Calc)", f"{calculated_cr*100:.2f}%", 
                          help=f"Based on {int(visitors_per_group_est)} visitors per group.")

            df["Unit Value (£)"] = df["Matched Policy"].map(product_ltv_map).fillna(0)
            df["Mix"] = df["Count"] / total_sales
            blended_val = (df["Unit Value (£)"] * df["Mix"]).sum()
            
            group_inputs[group] = {
                "CR_Initial": calculated_cr,
                "LTV_Per_User": blended_val,
                "Mix_Table": df
            }
            
            with c2:
                st.markdown("**Product Mix Analysis**")
                st.dataframe(df[["Matched Policy", "Count", "Unit Value (£)"]], height=150, use_container_width=True, hide_index=True)
                st.caption(f"**Avg LTV Generated per Sale:** £{blended_val:.2f}")

# --- PROJECTION ENGINE ---
st.divider()
st.header("3. Executive Summary (24 Month Rollout)")

if "Control" in group_inputs and len(group_inputs) > 1:
    
    calc_results = []
    months = 24
    control_data = group_inputs["Control"]
    
    # Control Baseline Projection
    control_monthly_rev = traffic_monthly * control_data["CR_Initial"] * control_data["LTV_Per_User"]
    control_total_rev = control_monthly_rev * months

    for name, data in group_inputs.items():
        if name == "Control":
            calc_results.append({
                "Group": name, "Total Rev": control_total_rev, "Net Profit": 0, "ROI": 0,
                "Revenue_Stream": [control_monthly_rev] * months
            })
            continue
            
        # Variant Projection (With Decay)
        initial_lift = data["CR_Initial"] - control_data["CR_Initial"]
        
        variant_rev_stream = []
        total_variant_rev = 0
        
        for m in range(months):
            # Decay the LIFT
            decayed_lift = initial_lift * ((1 - decay_rate) ** m)
            current_cr = max(control_data["CR_Initial"], control_data["CR_Initial"] + decayed_lift)
            
            monthly_rev = traffic_monthly * current_cr * data["LTV_Per_User"]
            variant_rev_stream.append(monthly_rev)
            total_variant_rev += monthly_rev
            
        incremental = total_variant_rev - control_total_rev
        profit = incremental - cost
        roi = (profit/cost)*100 if cost > 0 else 0
        
        calc_results.append({
            "Group": name,
            "Total Rev": total_variant_rev,
            "Net Profit": profit,
            "ROI": roi,
            "Revenue_Stream": variant_rev_stream
        })

    best_res = max([x for x in calc_results if x["Group"] != "Control"], key=lambda x: x["Net Profit"])
    
    # NARRATIVE
    st.subheader("Recommendation")
    
    horizon_label = "5-Year NPV" if is_finance else "2-Year Value"
    
    if best_res["Net Profit"] > 0:
        break_even_month = "N/A"
        monthly_diff = (best_res['Total Rev'] - control_total_rev) / 24
        if monthly_diff > 0:
            break_even_month = int(cost / monthly_diff)
        
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin:0'>✅ Recommended: {best_res['Group']}</h3>
            <p>Projected Outcome (24 Month Rollout):</p>
            <ul>
                <li><b>Net Profit ({horizon_label}):</b> £{best_res['Net Profit']:,.0f}</li>
                <li><b>ROI:</b> {best_res['ROI']:.0f}%</li>
                <li><b>Break Even:</b> Pays back cost in Month {break_even_month}</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        else:
        st.markdown(f"""
        <div class='error-box'>
            <h3 style='margin:0'>🛑 Not Recommended</h3>
            <p>{best_res['Group']} is projected to lose money.</p>
            <ul>
                <li><b>Net Loss:</b> £{abs(best_res['Net Profit']):,.0f}</li>
                <li>The lift generated is insufficient to cover the £{cost:,.0f} implementation cost given the traffic volume.</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        
    # VISUALS
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("**Monthly Value Generated (£)**")
        st.caption("This shows the total LTV generated each month. Notice the decay over time.")
        chart_df = pd.DataFrame()
        chart_df["Month"] = list(range(1, 25))
        chart_df["Control"] = calc_results[0]["Revenue_Stream"]
        for res in calc_results:
            if res["Group"] != "Control":
                chart_df[res["Group"]] = res["Revenue_Stream"]
        
        fig = px.line(chart_df, x="Month", y=chart_df.columns[1:], 
                     labels={"value": "Value Generated (£)", "variable": "Strategy"})
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.markdown("**Financial Summary**")
        summary_df = pd.DataFrame(calc_results)
        
        # --- FIXED TABLE FORMATTING ---
        # Using st.column_config to perform formatting instead of styling the dataframe object directly.
        # This prevents the SyntaxError from previous versions.
        st.dataframe(
            summary_df[["Group", "Total Rev", "Net Profit", "ROI"]],
            column_config={
                "Total Rev": st.column_config.NumberColumn(format="£%.0f"),
                "Net Profit": st.column_config.NumberColumn(format="£%.0f"),
                "ROI": st.column_config.NumberColumn(format="%.0f%%"),
            },
            use_container_width=True, 
            hide_index=True
        )

    # --- RISK SIMULATOR ---
    st.divider()
    st.header("4. Confidence Check (Risk Simulator)")
    st.markdown("Simulate **1,000 scenarios** varying inputs by ±10%.")
    
    if st.button("Run Risk Simulation", type="primary"):
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
                fig_risk.update_layout(xaxis_title="Net Profit (£)", showlegend=False, height=300)
                st.plotly_chart(fig_risk, use_container_width=True)

else:
    st.info("Please input data in the tabs above.")
