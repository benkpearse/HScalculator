import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib 

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI & LTV Calculator", layout="wide", page_icon="📊")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; }
    
    .mode-badge { padding: 8px 12px; border-radius: 5px; font-weight: bold; margin-bottom: 15px; display: inline-block; font-size: 0.9em; }
    .marketing-mode { background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
    .finance-mode { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    
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

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### Evaluate A/B Tests with Financial Precision")

with st.expander("📘 **Start Here: How to use this calculator**", expanded=True):
    st.markdown("""
    **1. Choose Your Engine (Sidebar):**
    * **Marketing Mode:** 2-Year View. Good for quick wins.
    * **Finance Mode:** 5-Year View with Discount Rates. Good for CFO approval.
    
    **2. Set Realistic Decay (Sidebar - New!):**
    * A/B test wins often fade ("Novelty Effect"). Use the **Performance Decay Slider** to model this drop-off over time.
    
    **3. Input Data:**
    * Paste your Excel product mix into the tabs below.
    """)

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Calculator Mode")
    mode_selection = st.radio("Select Engine:", ["Marketing Mode (Simple)", "Finance Mode (Advanced)"])
    is_finance = "Finance" in mode_selection
    
    st.divider()
    
    # --- NEW: PERFORMANCE DECAY SECTION ---
    st.header("2. Performance Decay")
    st.info("💡 **The Novelty Effect:** High conversion rates often drop after the launch hype.")
    
    decay_rate = st.slider("Monthly Lift Decay", 0, 20, 5, format="%d%%", 
                          help="How much of the 'winning gap' disappears each month? (e.g., 5% means the lift shrinks by 5% every month).") / 100.0
    
    st.divider()
    
    if is_finance:
        st.subheader("Finance Params")
        discount_rate = st.slider("Discount Rate (WACC)", 0, 15, 5, format="%d%%") / 100.0
    else:
        st.subheader("Marketing Params")
        global_retention = st.slider("Global Year 2 Retention", 50, 95, 80, format="%d%%") / 100.0
    
    st.subheader("Scope")
    num_variants = st.number_input("Number of Variants", 1, 5, 1)
    traffic_monthly = st.number_input("Monthly Traffic", value=10000, step=1000, help="Average visitors per month.")
    cost = st.number_input("Impl. Cost (£)", value=5000, step=500)

# --- ENGINE CONFIGURATION ---
product_ltv_map = {} 

st.header("1. Assumptions Engine")

if is_finance:
    st.markdown("<div class='mode-badge finance-mode'>🔓 FINANCE ENGINE: 5-Year NPV</div>", unsafe_allow_html=True)
    with st.expander("📊 **Edit Finance Matrix**", expanded=True):
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
    st.markdown("<div class='mode-badge marketing-mode'>🚀 MARKETING ENGINE: 2-Year Simple</div>", unsafe_allow_html=True)
    for p_name, p_price in PRICE_CATALOG.items():
        product_ltv_map[p_name] = p_price + (p_price * global_retention)

# --- INPUT SECTION ---
st.divider()
st.header("2. Test Data (Mix & Rates)")

variant_names = [f"Variant {i+1}" for i in range(num_variants)]
tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])
results = {}

# We need the Control CR to calculate lift for others
control_cr_input = 0.02 # default

# First pass to get inputs
group_inputs = {}

for i, group in enumerate(["Control"] + variant_names):
    with tabs[i]:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**{group} Data**")
            raw = st.text_area(f"Paste Mix {group}", height=100, key=f"p_{group}", 
                              placeholder="Name\tCount", label_visibility="collapsed")
            cr = st.number_input(f"Initial Conv. Rate (%) - {group}", value=2.0 if i==0 else 2.2, step=0.1, format="%.2f") / 100
        
        df = parse_paste_data(raw)
        
        if group == "Control":
            control_cr_input = cr

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
                st.dataframe(df[["Matched Policy", "Count", "Unit Value (£)"]], height=150, use_container_width=True, hide_index=True)
                st.caption(f"Blended LTV (per user): £{blended_val:.2f}")

# --- DECAY ENGINE CALCULATION ---
# Calculate Revenue over 24 Months considering Decay
st.divider()
st.header("3. Executive Summary (Adjusted for Decay)")

if "Control" in group_inputs and len(group_inputs) > 1:
    
    calc_results = []
    
    # We calculate projections for Control and Variants
    # Control assumes constant CR (No decay on baseline)
    control_data = group_inputs["Control"]
    control_rev_total = 0
    
    # 24 Month Projection
    months = 24
    
    # Calculate Control Baseline first
    # Control Revenue = Traffic * Control_CR * Control_LTV * 24 Months
    control_monthly_rev = traffic_monthly * control_data["CR_Initial"] * control_data["LTV_Per_User"]
    control_rev_total = control_monthly_rev * months

    for name, data in group_inputs.items():
        if name == "Control":
            calc_results.append({
                "Group": name, "Total Rev": control_rev_total, "Net Profit": 0, "ROI": 0
            })
            continue
            
        # Variant Calculation with Decay
        initial_lift = data["CR_Initial"] - control_data["CR_Initial"]
        
        total_variant_rev = 0
        monthly_crs = [] # For charting
        
        for m in range(months):
            # Lift decays each month: Lift * (1 - decay)^month
            current_lift = initial_lift * ((1 - decay_rate) ** m)
            
            # Variant CR cannot go below Control CR (floor)
            current_cr = max(control_data["CR_Initial"], control_data["CR_Initial"] + current_lift)
            
            monthly_crs.append(current_cr)
            
            # Revenue for this month
            monthly_rev = traffic_monthly * current_cr * data["LTV_Per_User"]
            total_variant_rev += monthly_rev
            
        # Financials
        incremental = total_variant_rev - control_rev_total
        profit = incremental - cost
        roi = (profit/cost)*100 if cost > 0 else 0
        
        calc_results.append({
            "Group": name,
            "Total Rev": total_variant_rev,
            "Net Profit": profit,
            "ROI": roi,
            "Chart_Data": monthly_crs
        })

    # FIND WINNER
    best_res = max([x for x in calc_results if x["Group"] != "Control"], key=lambda x: x["Net Profit"])
    
    # NARRATIVE
    if best_res["Net Profit"] > 0:
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin:0'>✅ Recommended: {best_res['Group']}</h3>
            <p>Even accounting for a <b>{decay_rate*100:.0f}% monthly decay</b> in performance, this strategy is profitable.</p>
            <ul>
                <li><b>Net Profit (24 Months):</b> £{best_res['Net Profit']:,.0f}</li>
                <li><b>ROI:</b> {best_res['ROI']:.0f}%</li>
            </ul>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='error-box'>
            <h3 style='margin:0'>🛑 Not Recommended</h3>
            <p>When we account for the <b>{decay_rate*100:.0f}% performance decay</b>, {best_res['Group']} loses money.</p>
            <ul>
                <li><b>Net Loss:</b> £{abs(best_res['Net Profit']):,.0f}</li>
                <li>The initial lift fades too quickly to cover the £{cost} cost.</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        
    # VISUALS
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Conversion Rate Decay")
        # Plot CR over time
        chart_df = pd.DataFrame()
        chart_df["Month"] = list(range(1, 25))
        chart_df["Control"] = control_data["CR_Initial"] * 100
        
        for res in calc_results:
            if "Chart_Data" in res:
                chart_df[res["Group"]] = [x*100 for x in res["Chart_Data"]]
                
        fig = px.line(chart_df, x="Month", y=chart_df.columns[1:], title="Performance Fade Over 2 Years (%)",
                     labels={"value": "Conversion Rate (%)", "variable": "Group"})
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("Total Financial Impact (24 Mo)")
        summary_df = pd.DataFrame(calc_results)
        st.dataframe(summary_df[["Group", "Total Rev", "Net Profit", "ROI"]].style.format({
            "Total Rev": "£{:,.0f}", "Net Profit": "£{:,.0f}", "ROI": "{:.0f}%"
        }), use_container_width=True)
else:
    st.info("Please input data in the tabs above.")
