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
    
    /* Mode Badges */
    .mode-badge { padding: 8px 12px; border-radius: 5px; font-weight: bold; margin-bottom: 15px; display: inline-block; font-size: 0.9em; }
    .marketing-mode { background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
    .finance-mode { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    
    /* Result Boxes */
    .success-box { padding: 20px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 20px; border-radius: 4px; color: #155724; }
    .error-box { padding: 20px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 20px; border-radius: 4px; color: #721c24; }
    
    /* Section Headers */
    .section-header { font-size: 1.2rem; font-weight: 600; color: #333; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 1. HARDCODED PRICE BOOK (Base Prices) ---
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

# --- HEADER & ONBOARDING ---
st.title("💼 Strategic ROI & LTV Calculator")
st.markdown("### Evaluate the Financial Impact of A/B Tests")

with st.expander("📘 **Start Here: Quick Guide**", expanded=True):
    st.markdown("""
    **Goal:** Calculate if a new strategy (Variant) is profitable compared to the baseline (Control).
    
    1.  **Configure (Sidebar):** Select your Mode (Marketing vs Finance) and set project costs.
    2.  **Input Data (Tabs):** Paste your product mix (Name | Count) for each group.
    3.  **Review (Bottom):** See the Executive Summary and Revenue Decay Charts.
    """)

# --- SIDEBAR: RESTRUCTURED LOGIC ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # --- STEP 1: ENGINE ---
    st.markdown("<div class='section-header'>1. Select Engine</div>", unsafe_allow_html=True)
    mode_selection = st.radio("Calculation Mode:", 
                             ["Marketing Mode (Simple)", "Finance Mode (Advanced)"],
                             help="**Marketing:** Uses a simple 2-Year LTV.\n**Finance:** Uses a 5-Year NPV model with granular retention settings.")
    is_finance = "Finance" in mode_selection
    
    # --- STEP 2: SCOPE ---
    st.markdown("<div class='section-header'>2. Project Scope</div>", unsafe_allow_html=True)
    
    num_variants = st.number_input("Variants Tested", 1, 5, 1, 
                                  help="Excluding Control, how many new versions did you test?")
    
    traffic_monthly = st.number_input("Monthly Traffic", value=10000, step=1000, 
                                     help="How many visitors does this page/journey get per month?")
    
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500, 
                          help="Total cost (Dev + Marketing) to fully roll out the winning strategy.")

    # --- STEP 3: DYNAMICS ---
    st.markdown("<div class='section-header'>3. Market Dynamics</div>", unsafe_allow_html=True)
    
    st.info("📉 **Performance Decay:** A/B test wins often fade over time as the 'novelty' wears off.")
    decay_rate = st.slider("Monthly Lift Decay", 0, 20, 5, format="%d%%",
                          help="If set to 5%, the 'gap' between Variant and Control shrinks by 5% every month.") / 100.0
    
    if is_finance:
        st.write("---")
        st.markdown("**Finance Settings**")
        discount_rate = st.slider("Discount Rate (WACC)", 0, 15, 5, format="%d%%", 
                                 help="Used for Net Present Value (NPV). Future money is worth less than today's money.") / 100.0
    else:
        st.write("---")
        st.markdown("**Marketing Settings**")
        global_retention = st.slider("Global Year 2 Retention", 50, 95, 80, format="%d%%",
                                    help="Percentage of Year 1 customers who renew for Year 2.") / 100.0

# --- MAIN CONTENT ---

# --- ENGINE CONFIGURATION ---
product_ltv_map = {} 

st.header("1. Financial Assumptions")

if is_finance:
    st.markdown("<div class='mode-badge finance-mode'>🔓 FINANCE ENGINE: 5-Year NPV Model</div>", unsafe_allow_html=True)
    
    with st.expander("📊 **Edit Finance Matrix (Pricing & Retention Curves)**", expanded=True):
        st.caption("Detailed 5-Year cash flow settings per product.")
        
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
            # Y2
            cohort *= (row["Ret Y1->Y2 (%)"]/100)
            cash_flows.append(cohort * row["Price Y2 (£)"])
            # Y3
            cohort *= (row["Ret Y2->Y3 (%)"]/100)
            cash_flows.append(cohort * row["Price Y3 (£)"])
            # Y4
            cohort *= (row["Ret Y3->Y4 (%)"]/100)
            cash_flows.append(cohort * row["Price Y4 (£)"])
            # Y5
            cohort *= (row["Ret Y4->Y5 (%)"]/100)
            cash_flows.append(cohort * row["Price Y5 (£)"])
            
            npv_manual = sum([cf / ((1+discount_rate)**t) for t, cf in enumerate(cash_flows)])
            product_ltv_map[row["Product"]] = npv_manual
else:
    st.markdown("<div class='mode-badge marketing-mode'>🚀 MARKETING ENGINE: 2-Year Simple Model</div>", unsafe_allow_html=True)
    for p_name, p_price in PRICE_CATALOG.items():
        product_ltv_map[p_name] = p_price + (p_price * global_retention)

# --- INPUT SECTION ---
st.divider()
st.header("2. Input Test Data")
st.info("👇 **Instructions:** Paste your Excel data (Product Name | Count) into the tabs below.")

variant_names = [f"Variant {i+1}" for i in range(num_variants)]
tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])

# Data Collection
group_inputs = {}

for i, group in enumerate(["Control"] + variant_names):
    with tabs[i]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**{group} Input**")
            raw = st.text_area(f"Paste {group}", height=120, key=f"p_{group}", 
                              placeholder="Plumbing...\t50\nGas Boiler\t20", label_visibility="collapsed")
            cr = st.number_input(f"Initial Conv. Rate (%) - {group}", value=2.0 if i==0 else 2.2, step=0.1, format="%.2f",
                                help="The conversion rate achieved during the test period.") / 100
        
        df = parse_paste_data(raw)
        
        if not df.empty:
            df["Unit Value (£)"] = df["Matched Policy"].map(product_ltv_map).fillna(0)
            total_sales = df["Count"].sum()
            df["Mix"] = df["Count"] / total_sales
            blended_val = (df["Unit Value (£)"] * df["Mix"]).sum()
            
            group_inputs[group] = {
                "CR_Initial": cr,
                "LTV_Per_User": blended_val,
                "Mix_Table": df
            }
            
            with c2:
                st.markdown("**Mix Analysis**")
                st.dataframe(df[["Matched Policy", "Count", "Unit Value (£)"]], height=150, use_container_width=True, hide_index=True)
                st.caption(f"**Blended Value (Per User):** £{blended_val:.2f}")

# --- DECAY ENGINE CALCULATION ---
st.divider()
st.header("3. Executive Summary & Revenue Projection")

if "Control" in group_inputs and len(group_inputs) > 1:
    
    calc_results = []
    
    # 24 Month Projection Loop
    months = 24
    control_data = group_inputs["Control"]
    
    # 1. Baseline (Control) Revenue Stream
    # Control assumes 0 decay (it is the baseline)
    # Rev = Traffic * CR * LTV
    control_monthly_rev = traffic_monthly * control_data["CR_Initial"] * control_data["LTV_Per_User"]
    control_total_rev = control_monthly_rev * months

    for name, data in group_inputs.items():
        if name == "Control":
            calc_results.append({
                "Group": name, "Total Rev": control_total_rev, "Net Profit": 0, "ROI": 0,
                "Revenue_Stream": [control_monthly_rev] * months
            })
            continue
            
        # 2. Variant Revenue Stream (With Decay)
        initial_lift = data["CR_Initial"] - control_data["CR_Initial"]
        
        variant_rev_stream = []
        total_variant_rev = 0
        
        for m in range(months):
            # Apply Decay to the LIFT only
            decayed_lift = initial_lift * ((1 - decay_rate) ** m)
            
            # Current Month CR
            current_cr = control_data["CR_Initial"] + decayed_lift
            
            # Floor: Can't drop below Control (unless negative lift initially, but simplified here)
            if initial_lift > 0:
                current_cr = max(control_data["CR_Initial"], current_cr)
            
            monthly_rev = traffic_monthly * current_cr * data["LTV_Per_User"]
            variant_rev_stream.append(monthly_rev)
            total_variant_rev += monthly_rev
            
        # Financials
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

    # FIND WINNER
    best_res = max([x for x in calc_results if x["Group"] != "Control"], key=lambda x: x["Net Profit"])
    
    # NARRATIVE
    st.subheader("Recommendation")
    if best_res["Net Profit"] > 0:
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin:0'>✅ Recommended: {best_res['Group']}</h3>
            <p>Even with a <b>{decay_rate*100:.0f}% monthly decay</b>, this strategy yields a profit.</p>
            <ul>
                <li><b>Net Profit (2 Years):</b> £{best_res['Net Profit']:,.0f}</li>
                <li><b>ROI:</b> {best_res['ROI']:.0f}%</li>
            </ul>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='error-box'>
            <h3 style='margin:0'>🛑 Not Recommended</h3>
            <p>Due to the <b>{decay_rate*100:.0f}% monthly decay</b>, {best_res['Group']} loses money over time.</p>
            <ul>
                <li><b>Net Loss:</b> £{abs(best_res['Net Profit']):,.0f}</li>
                <li>The initial lift fades too fast to recover the £{cost:,.0f} cost.</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        
    # VISUALS
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("**Monthly Revenue Projection (£)**")
        # Build Chart Data
        chart_df = pd.DataFrame()
        chart_df["Month"] = list(range(1, 25))
        
        # Add Control Line
        chart_df["Control"] = calc_results[0]["Revenue_Stream"]
        
        # Add Variants
        for res in calc_results:
            if res["Group"] != "Control":
                chart_df[res["Group"]] = res["Revenue_Stream"]
        
        fig = px.line(chart_df, x="Month", y=chart_df.columns[1:], 
                     labels={"value": "Monthly Revenue (£)", "variable": "Strategy"})
        
        # Highlight the Decay area
        fig.add_annotation(x=12, y=chart_df[best_res["Group"]].iloc[11],
                          text="Decay Impact", showarrow=True, arrowhead=1)
        
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Notice how the Variant line (colored) converges toward the Control line (blue) as the lift decays.")
        
    with c2:
        st.markdown("**Financial Summary (24 Months)**")
        summary_df = pd.DataFrame(calc_results)
        st.dataframe(summary_df[["Group", "Total Rev", "Net Profit", "ROI"]].style.format({
            "Total Rev": "£{:,.0f}", "Net Profit": "£{:,.0f}", "ROI": "{:.0f}%"
        }), use_container_width=True, hide_index=True)

else:
    st.info("Please input data in the tabs above to calculate projections.")
