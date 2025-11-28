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
    
    /* Mode Badges */
    .mode-badge { padding: 8px 12px; border-radius: 5px; font-weight: bold; margin-bottom: 15px; display: inline-block; font-size: 0.9em; }
    .marketing-mode { background-color: #e3f2fd; color: #0d47a1; border: 1px solid #90caf9; }
    .finance-mode { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    
    /* Result Boxes */
    .success-box { padding: 20px; background-color: #d4edda; border-left: 5px solid #28a745; margin-bottom: 20px; border-radius: 4px; color: #155724; }
    .error-box { padding: 20px; background-color: #f8d7da; border-left: 5px solid #dc3545; margin-bottom: 20px; border-radius: 4px; color: #721c24; }
    
    /* Tooltip Helper */
    .tooltip-icon { color: #6c757d; font-size: 0.8em; cursor: help; }
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
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### Evaluate A/B Tests with Financial Precision")

with st.expander("📘 **Start Here: How to use this calculator**", expanded=True):
    st.markdown("""
    **1. Choose Your Engine (Sidebar):**
    * **Marketing Mode (Default):** Great for quick estimates. Uses a simple **2-Year LTV** and global retention assumptions.
    * **Finance Mode (Advanced):** Unlocks a **5-Year NPV** model where you can set specific renewal rates and price hikes for *every* product.
    
    **2. Define The Test:**
    * Input your traffic and costs in the Sidebar.
    
    **3. Input Data (Main Screen):**
    * For each Tab (Control, Variant A, etc.), copy the **Product Name** and **Count** columns from Excel and paste them into the box.
    * The app auto-detects pricing and corrects typos.
    
    **4. Read the Results:**
    * Scroll down to the **Executive Summary** for a "Green Light / Red Light" recommendation.
    """)

# --- SIDEBAR: SETTINGS & GLOSSARY ---
with st.sidebar:
    st.header("1. Calculator Mode")
    
    mode_selection = st.radio("Select Engine:", 
                             ["Marketing Mode (Simple)", "Finance Mode (Advanced)"],
                             help="Choose 'Marketing' for speed (2-Year view) or 'Finance' for precision (5-Year NPV with Discount Rates).")
    
    is_finance = "Finance" in mode_selection
    
    st.divider()
    
    if is_finance:
        st.subheader("Finance Parameters")
        st.info("Using 5-Year Discounted Cash Flow (DCF).")
        discount_rate = st.slider("Discount Rate (WACC)", 0, 15, 5, format="%d%%", 
                                 help="The Annual Discount Rate. We use this to calculate Net Present Value (NPV), as money in the future is worth less than money today.") / 100.0
    else:
        st.subheader("Marketing Parameters")
        st.info("Using Simple 2-Year Horizon.")
        global_retention = st.slider("Global Year 2 Retention", 50, 95, 80, format="%d%%",
                                    help="The percentage of Year 1 customers expected to renew for Year 2.") / 100.0
    
    st.subheader("Scope Assumptions")
    num_variants = st.number_input("Number of Variants", 1, 5, 1, help="Excluding the Control group, how many new versions did you test?")
    traffic = st.number_input("Traffic per Group", value=10000, step=1000, help="Total visitors/users exposed to each variation.")
    cost = st.number_input("Impl. Cost (£)", value=5000, step=500, help="Total project cost (Dev + Marketing) to implement the winning strategy.")

    st.divider()
    st.markdown("### 📚 Glossary")
    st.markdown("""
    * **LTV:** Lifetime Value of a customer.
    * **NPV:** Net Present Value (Discounted Cash Flow).
    * **Mix Shift:** Changing *what* people buy (e.g. selling more Gold plans than Basic).
    """)

# --- ENGINE CONFIGURATION ---
product_ltv_map = {} # Stores the calculated LTV for every product

st.header("1. Assumptions Engine")

if is_finance:
    st.markdown("<div class='mode-badge finance-mode'>🔓 FINANCE ENGINE ACTIVE: 5-Year Granular Control</div>", unsafe_allow_html=True)
    
    with st.expander("📊 **Edit Finance Matrix (Pricing & Retention Curves)**", expanded=True):
        st.markdown("""
        **Instructions:** This grid controls the 5-Year Cash Flow model. 
        You can set unique **Retention Rates** and **Price Points** for Years 2-5 for every single product.
        """)
        
        # Build Grid from Catalog
        rows = []
        for p_name, p_price in PRICE_CATALOG.items():
            rows.append({
                "Product": p_name,
                "Y1 Price": p_price,
                # Defaults
                "Ret Y1->Y2 (%)": 80, "Price Y2 (£)": p_price * 1.05,
                "Ret Y2->Y3 (%)": 85, "Price Y3 (£)": p_price * 1.10,
                "Ret Y3->Y4 (%)": 90, "Price Y4 (£)": p_price * 1.15,
                "Ret Y4->Y5 (%)": 90, "Price Y5 (£)": p_price * 1.20,
            })
        
        # Edit Grid
        matrix_df = st.data_editor(
            pd.DataFrame(rows),
            hide_index=True,
            height=300,
            use_container_width=True,
            column_config={
                "Product": st.column_config.TextColumn(disabled=True), 
                "Y1 Price": st.column_config.NumberColumn(format="£%.2f", disabled=True),
                "Price Y2 (£)": st.column_config.NumberColumn(format="£%.2f"),
                "Price Y3 (£)": st.column_config.NumberColumn(format="£%.2f"),
                "Price Y4 (£)": st.column_config.NumberColumn(format="£%.2f"),
                "Price Y5 (£)": st.column_config.NumberColumn(format="£%.2f"),
            }
        )
        
        # CALCULATION ENGINE: 5-YEAR NPV
        for idx, row in matrix_df.iterrows():
            # Year 1 (Cash)
            cash_flows = [row["Y1 Price"]]
            
            # Years 2-5 (Probability Adjusted Cash)
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
            
            # Manual NPV Calculation
            npv_manual = sum([cf / ((1+discount_rate)**t) for t, cf in enumerate(cash_flows)])
            product_ltv_map[row["Product"]] = npv_manual

else:
    st.markdown("<div class='mode-badge marketing-mode'>🚀 MARKETING ENGINE ACTIVE: 2-Year Simple View</div>", unsafe_allow_html=True)
    st.caption("ℹ️ Calculating LTV as: Year 1 Price + (Year 1 Price × Global Retention).")
    # CALCULATION ENGINE: 2-YEAR SIMPLE
    for p_name, p_price in PRICE_CATALOG.items():
        product_ltv_map[p_name] = p_price + (p_price * global_retention)

# --- INPUT SECTION ---
st.divider()
st.header("2. Test Data (Product Mix)")
st.info("👇 **Action:** Paste the 'Product Name' and 'Sales Count' columns from your Excel report into the tabs below.")

variant_names = [f"Variant {i+1}" for i in range(num_variants)]
tabs = st.tabs(["🅰️ Control Group"] + [f"🅱️ {v}" for v in variant_names])
results = {}

for i, group in enumerate(["Control"] + variant_names):
    with tabs[i]:
        c1, c2, c3 = st.columns([1.5, 2, 1])
        with c1:
            st.markdown(f"**Paste {group} Data**")
            raw = st.text_area(f"Data {group}", height=150, key=f"p_{group}", 
                              placeholder="Plumbing...\t50\nGas Boiler\t20", 
                              label_visibility="collapsed",
                              help="Copy from Excel (Column A & B) and paste here.")
            
            cr = st.number_input(f"Conv. Rate (%) - {group}", value=2.0 if i==0 else 2.2, step=0.1, format="%.2f",
                                help=f"The final conversion rate observed for {group}.") / 100
            
        df = parse_paste_data(raw)
        
        if not df.empty:
            # LOOKUP VALUE BASED ON ACTIVE ENGINE
            df["Unit Value (£)"] = df["Matched Policy"].map(product_ltv_map).fillna(0)
            
            total_sales = df["Count"].sum()
            df["Mix"] = df["Count"] / total_sales
            
            # Metrics
            blended_val = (df["Unit Value (£)"] * df["Mix"]).sum()
            total_rev = traffic * cr * blended_val
            
            results[group] = {"CR": cr, "UnitVal": blended_val, "Revenue": total_rev}
            
            with c2: 
                st.markdown("**Validation**")
                st.dataframe(df[["Matched Policy", "Count", "Base Price", "Unit Value (£)"]], 
                             height=150, use_container_width=True, hide_index=True,
                             column_config={"Unit Value (£)": st.column_config.NumberColumn(help="Calculated LTV based on selected Engine.")})
            with c3:
                st.markdown("**Metrics**")
                st.metric("Blended LTV", f"£{blended_val:.2f}", help="Weighted Average Value per User")
                st.metric("Proj. Revenue", f"£{total_rev:,.0f}", help="Traffic x CR x LTV")
        else:
            with c2: st.info(f"Paste data for {group} to see calculations.")

# --- RESULTS SECTION ---
if "Control" in results and len(results) > 1:
    st.divider()
    st.header("3. Executive Summary")
    
    best_v = max(results, key=lambda x: results[x]['Revenue'] if x != 'Control' else -1)
    base_rev = results["Control"]["Revenue"]
    best_rev = results[best_v]["Revenue"]
    profit = (best_rev - base_rev) - cost
    roi = (profit/cost)*100 if cost > 0 else 0
    
    # NARRATIVE GENERATOR
    horizon = "5-Year NPV" if is_finance else "2-Year Nominal"
    
    if profit > 0:
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin:0'>✅ Recommendation: Green Light for {best_v}</h3>
            <p>Based on the <b>{horizon}</b> model, {best_v} is the clear winner.</p>
            <ul>
                <li>It generates <b>£{profit:,.0f}</b> in pure profit (after covering the £{cost} cost).</li>
                <li>The Return on Investment (ROI) is <b>{roi:.0f}%</b>.</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        

[Image of Financial Dashboard]
 # Trigger for diagram of dashboard
    else:
        st.markdown(f"""
        <div class='error-box'>
            <h3 style='margin:0'>🛑 Recommendation: Do Not Roll Out</h3>
            <p>Based on the <b>{horizon}</b> model, {best_v} is not financially viable.</p>
            <ul>
                <li>Rolling this out would result in a net loss of <b>£{abs(profit):,.0f}</b>.</li>
                <li>The revenue uplift does not cover the £{cost} implementation cost.</li>
            </ul>
        </div>""", unsafe_allow_html=True)
        
    # TABLE
    st.subheader("Financial Breakdown")
    rows = []
    for k, v in results.items():
        is_ctrl = k == "Control"
        inc = v["Revenue"] - base_rev
        prof = inc - cost if not is_ctrl else 0
        rows.append({
            "Strategy": k,
            "Conv Rate": f"{v['CR']*100:.2f}%",
            f"Avg Value ({horizon})": f"£{v['UnitVal']:.2f}",
            "Total Revenue": f"£{v['Revenue']:,.0f}",
            "Net Profit": f"£{prof:,.0f}" if not is_ctrl else "-",
        })
    st.table(pd.DataFrame(rows))
    
    # VISUALS
    c_chart, c_risk = st.columns(2)
    with c_chart:
        st.subheader("Revenue Projection")
        df_chart = pd.DataFrame([{"Group": k, "Rev": v["Revenue"]} for k,v in results.items()])
        fig = px.bar(df_chart, x="Group", y="Rev", title=f"Total Value ({horizon})", color="Group", text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
        
    with c_risk:
        st.subheader("Confidence Check (Monte Carlo)")
        st.markdown(f"Simulate **1,000 scenarios** to see if {best_v} is a safe bet given market volatility.")
        
        if st.button("Run Simulation"):
            sims = 1000
            # Volatility setting
            vol = 0.10
            
            # Best vs Control Inputs
            v_cr = results[best_v]["CR"]
            v_val = results[best_v]["UnitVal"]
            c_cr = results["Control"]["CR"]
            c_val = results["Control"]["UnitVal"]
            
            # Simulations
            s_v_cr = np.random.normal(v_cr, v_cr*vol, sims)
            s_c_cr = np.random.normal(c_cr, c_cr*(vol*0.5), sims)
            
            # Value fluctuation (Proxy for retention/price variance)
            s_val_mult = np.random.normal(1.0, 0.05, sims)
            
            profit_arr = (traffic * s_v_cr * v_val * s_val_mult) - (traffic * s_c_cr * c_val * s_val_mult) - cost
            win_rate = (np.sum(profit_arr > 0) / sims) * 100
            
            st.metric("Probability of Profit", f"{win_rate:.1f}%")
            if win_rate > 80: st.success("Low Risk: Highly likely to be profitable.")
            elif win_rate > 50: st.warning("Moderate Risk: It's a coin toss.")
            else: st.error("High Risk: Likely to lose money.")
