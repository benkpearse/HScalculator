import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import difflib  # For fuzzy matching names

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic ROI Calculator", layout="wide", page_icon="🇬🇧")

# --- CUSTOM CSS FOR POLISH ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
    .stAlert { padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 1. HARDCODED PRICE BOOK (UK DATA) ---
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

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & ROI Calculator")
st.markdown("### From Product Mix to Bottom Line Profit")

# --- "HOW TO USE" SECTION ---
with st.expander("📘 Start Here: How to use this calculator", expanded=True):
    st.markdown("""
    **Goal:** Calculate the true financial impact of your A/B test by accounting for the specific products users bought.
    
    1.  **Step 1: Paste Your Data (Section 1)**
        * Copy two columns from your Excel report: **Product Name** and **Sales Count**.
        * Paste them into the box below. The app will automatically find the prices.
    2.  **Step 2: Set The Context (Sidebar)**
        * Input your traffic volume and project costs.
    3.  **Step 3: Analyze Results (Section 2)**
        * Input the Conversion Rates from your test.
        * Check the **Executive Summary** to see if the project is profitable.
    """)

# --- SIDEBAR: SETTINGS & GLOSSARY ---
with st.sidebar:
    st.header("⚙️ Simulation Settings")
    
    st.subheader("1. Traffic Volume")
    traffic = st.number_input("Total Visitors", value=10000, step=1000, 
                             help="Total number of visitors in the test group (or monthly traffic).")
    
    st.subheader("2. Investment")
    cost = st.number_input("Implementation Cost (£)", value=5000, step=500,
                          help="Total cost to build/market this feature.")
    
    st.divider()
    
    st.subheader("3. Retention Assumptions")
    st.caption("We assume Year 2 Price = Year 1 Price.")
    retention_rate = st.slider("Year 2 Renewal Rate", 50, 95, 80, format="%d%%",
                              help="Percentage of customers who renew the policy for a second year.") / 100.0
    
    st.divider()
    st.subheader("📚 Glossary")
    st.markdown("""
    * **Blended ARPU:** Average Revenue Per User, weighted by the mix of products sold.
    * **LTV (Lifetime Value):** Total value of a customer over 2 years (Acquisition + Renewal).
    * **Break-Even:** The conversion rate required to pay back the initial cost.
    """)

# --- SECTION 1: PRODUCT MIX INPUT ---
st.header("1. The Product Mix")
st.info("👇 **Action:** Copy your product mix from Excel and paste it below to calculate your Blended Price.")

col_paste, col_preview = st.columns([1, 1])

with col_paste:
    st.markdown("##### Paste Excel Data Here (Name | Count)")
    placeholder = "Example:\nPlumbing and Drainage Plus\t50\nGas Boiler\t20"
    raw_data = st.text_area("Data Input", height=300, placeholder=placeholder, label_visibility="collapsed")

# --- PARSING LOGIC ---
parsed_rows = []
total_sales_count = 0

if raw_data:
    lines = raw_data.strip().split('\n')
    for line in lines:
        # Flexible splitter: Tab (Excel default), Comma (CSV), or Pipe
        if '\t' in line: parts = line.split('\t')
        elif ',' in line: parts = line.split(',')
        else: parts = line.rsplit(' ', 1) # Fallback

        if len(parts) >= 2:
            p_name = parts[0].strip()
            # Clean number string (remove currency symbols or commas)
            p_count_str = parts[1].strip().replace(',', '').replace('£', '')
            
            try:
                p_count = float(p_count_str)
            except ValueError:
                p_count = 0
            
            # PRICE LOOKUP
            matched_price = 0
            status = "⚠️ Price Not Found"
            
            # Exact match check
            if p_name in PRICE_CATALOG:
                matched_price = PRICE_CATALOG[p_name]
                status = "✅ Found"
            else:
                # Case insensitive check
                for cat_name, cat_price in PRICE_CATALOG.items():
                    if p_name.lower() == cat_name.lower():
                        matched_price = cat_price
                        p_name = cat_name # Use correct casing
                        status = "✅ Found"
                        break
            
            parsed_rows.append({
                "Policy Name": p_name,
                "Sales Count": p_count,
                "Price (£)": matched_price,
                "Status": status
            })
            total_sales_count += p_count

# Create DataFrame
if parsed_rows:
    df = pd.DataFrame(parsed_rows)
else:
    df = pd.DataFrame(columns=["Policy Name", "Sales Count", "Price (£)", "Status"])

# --- DISPLAY & CALCS ---
if not df.empty and total_sales_count > 0:
    # 1. Calculate Weights
    df["Mix %"] = df["Sales Count"] / total_sales_count
    
    # 2. Calculate LTV (Year 2 Price = Year 1 Price)
    # LTV = Price + (Price * Retention)
    df["LTV Contribution"] = df["Price (£)"] + (df["Price (£)"] * retention_rate)
    
    # 3. Weighted Averages
    avg_price = (df["Price (£)"] * df["Mix %"]).sum()
    blended_ltv = (df["LTV Contribution"] * df["Mix %"]).sum()

    with col_preview:
        st.markdown("##### Recognized Product Mix")
        st.dataframe(
            df[["Policy Name", "Sales Count", "Price (£)", "Status"]],
            column_config={
                "Price (£)": st.column_config.NumberColumn(format="£%.2f"),
                "Sales Count": st.column_config.NumberColumn(format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Error handling for typos
        unknowns = df[df["Status"].str.contains("Not Found")]
        if not unknowns.empty:
            st.warning(f"⚠️ Warning: Could not find pricing for {len(unknowns)} items. They are calculated as £0.")

    # 4. Unit Economics Display
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg. Year 1 Revenue", f"£{avg_price:.2f}", help="Weighted average price based on the mix above.")
    m2.metric("Blended LTV (2-Year)", f"£{blended_ltv:.2f}", help="Includes Year 1 + (Year 2 * Retention Rate)")
    m3.caption(f"**Note:** This LTV assumes a {retention_rate*100:.0f}% renewal rate for Year 2.")

    # --- SECTION 2: PERFORMANCE ---
    st.header("2. Performance & Financials")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### 🅰️ Baseline Strategy")
        cv_control = st.number_input("Current Conversion Rate (%)", value=2.0, format="%.2f") / 100
        rev_control = traffic * cv_control * blended_ltv
        
    with c2:
        st.markdown("#### 🅱️ New Strategy")
        cv_variant = st.number_input("New Conversion Rate (%)", value=2.2, format="%.2f") / 100
        rev_variant = traffic * cv_variant * blended_ltv
        
    # Break Even Math
    be_revenue_target = rev_control + cost
    be_cr = be_revenue_target / (traffic * blended_ltv) if (traffic * blended_ltv) > 0 else 0
    be_lift_needed = (be_cr - cv_control) / cv_control
    
    with c3:
        st.markdown("#### 🎯 The Target")
        if be_cr > 1.0:
             st.error("Cost is too high to break even.")
        else:
            st.markdown(f"To cover the **£{cost:,}** cost, you need:")
            st.metric(
                "Break-Even Conv. Rate", 
                f"{be_cr*100:.2f}%", 
                delta=f"{be_lift_needed:.1%} lift needed",
                delta_color="inverse",
                help="If your New Strategy is below this number, you are losing money."
            )

    # --- EXECUTIVE SUMMARY ---
    st.divider()
    st.subheader("🚀 Executive Summary")
    
    incremental_val = rev_variant - rev_control
    roi = ((incremental_val - cost) / cost) * 100 if cost > 0 else 0
    net_profit = incremental_val - cost
    
    # Dynamic Storytelling
    if net_profit > 0:
        st.success(f"✅ **Green Light:** This strategy is projected to generate **£{net_profit:,.0f}** in pure profit over 2 years.")
    else:
        st.error(f"⚠️ **Caution:** This strategy is projected to **lose £{abs(net_profit):,.0f}**. The lift in conversion is not enough to cover the implementation costs.")
        
    k1, k2, k3 = st.columns(3)
    k1.metric("Incremental Revenue", f"£{incremental_val:,.0f}", help="Total extra cash generated vs the old strategy.")
    k2.metric("Return on Investment (ROI)", f"{roi:.0f}%", help="Net Profit / Cost.")
    k3.metric("Net Profit", f"£{net_profit:,.0f}", help="Revenue minus Costs.")

    # --- SECTION 3: RISK SIMULATOR ---
    st.divider()
    st.header("🎲 Risk & Confidence Analysis")
    st.markdown("Real life isn't a single number. This tool simulates **1,000 scenarios** to see if your strategy is safe.")
    
    if st.button("Run Risk Simulation"):
        with st.spinner("Simulating 1,000 futures..."):
            sims = 1000
            volatility = 0.10 # 10% variance
            
            # Randomized Inputs
            sim_cv = np.random.normal(cv_variant, cv_variant * volatility, sims)
            sim_retention = np.random.normal(retention_rate, retention_rate * 0.05, sims) # Less volatile
            
            # Randomized LTV
            sim_ltv = avg_price + (avg_price * sim_retention)
            
            # Randomized Profit
            sim_rev = traffic * sim_cv * sim_ltv
            baseline = traffic * cv_control * blended_ltv
            sim_profit = (sim_rev - baseline) - cost
            
            # Stats
            wins = np.sum(sim_profit > 0)
            win_rate = (wins / sims) * 100
            
            r1, r2 = st.columns([1, 2])
            with r1:
                st.markdown(f"### Probability of Profit: :blue[{win_rate:.1f}%]")
                if win_rate > 80: st.success("Analysis: Low Risk.")
                elif win_rate > 50: st.warning("Analysis: Moderate Risk.")
                else: st.error("Analysis: High Risk.")
                
            with r2:
                fig = px.histogram(x=sim_profit, nbins=30, title="Profit/Loss Distribution", color_discrete_sequence=['#00CC96'])
                fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Break Even")
                fig.update_layout(xaxis_title="Net Profit (£)", showlegend=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

else:
    # Empty State Message
    st.info("👈 **Waiting for data:** Paste your product mix on the left to unlock the calculator.")
    with st.expander("Show Valid Product List (Reference)"):
        st.json(PRICE_CATALOG)
