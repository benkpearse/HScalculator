import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Insurance ROI & Strategy Simulator", layout="wide", page_icon="💼")

# --- CUSTOM CSS FOR POLISH ---
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
    .stAlert { padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER & ONBOARDING ---
st.title("💼 Strategy Impact & Risk Calculator")
st.markdown("### From Conversion Rate to Bottom Line ROI")

# --- "HOW TO USE" SECTION (RESTORED) ---
with st.expander("📘 Start Here: How to use this calculator", expanded=True):
    st.markdown("""
    **Goal:** Determine if your A/B test is actually profitable after accounting for product mix and customer retention.
    
    1.  **Step 1: Define Your Products (Section 1)**
        * Edit the table to match the insurance plans you offer. 
        * Input the **"Observed Mix"**: If 100 people bought policies, how many bought Basic vs. Gold?
        * *(Optional)* If you know the retention rates for each specific plan, toggle "Show Advanced" to input them.
    
    2.  **Step 2: Set The Stakes (Sidebar)**
        * Enter the total traffic and the cost to implement this strategy.
    
    3.  **Step 3: The "Hurdle" (Section 2)**
        * Look at the **Break-Even Target**. This tells you the minimum Conversion Rate you need to hit to cover your costs. 
    
    4.  **Step 4: Enter Results (Section 2)**
        * Input your **Current** and **New** conversion rates to see the projected ROI.
        
    5.  **Step 5: Sanity Check (Section 4)**
        * Run the **Risk Simulator** to see the probability of losing money if market conditions fluctuate.
    """)

# --- SIDEBAR: GLOBAL SETTINGS & GLOSSARY ---
with st.sidebar:
    st.header("⚙️ Simulation Settings")
    
    st.subheader("1. Traffic Volume")
    traffic = st.number_input("Total Visitors", value=10000, step=1000, 
                             help="The total number of users in the test group (or projected monthly traffic).")
    
    st.subheader("2. Investment Cost")
    cost = st.number_input("Implementation Cost ($)", value=5000, step=500, 
                          help="Total cost of the project (Dev hours + Marketing spend).")
    
    st.divider()
    
    st.subheader("📚 Quick Glossary")
    st.markdown("""
    * **LTV (Lifetime Value):** Total value of a customer over 2 years (Acquisition + Renewal).
    * **Mix Shift:** When users switch from expensive plans to cheaper ones (or vice versa).
    * **Retention:** The % of customers who renew for Year 2.
    """)
    
    st.divider()
    st.caption("Global Defaults")
    global_retention = st.slider("Baseline Renewal Rate", 50, 95, 85, format="%d%%",
                                help="If you don't know the specific retention per product, we use this average.") / 100.0

# --- SECTION 1: PRODUCT MIX & RETENTION ---
st.header("1. The Product Mix")
st.info("👇 **Action:** Edit the table below to reflect what customers actually bought during the test.")

# Toggle for the "Finance Team" view
show_advanced = st.checkbox("Show Advanced Retention (Per-Product Settings)", value=False, 
                           help="Check this if you know that 'Basic' users cancel more often than 'Premium' users.")

col_input, col_summ = st.columns([2, 1])

with col_input:
    # We start with specific retention rates if the finance team knows them
    default_data = {
        "Policy Name": ["Basic Cover", "Gold Cover", "Platinum Cover"],
        "Year 1 Price ($)": [150, 300, 500],
        "Year 2 Price ($)": [175, 350, 550],
        "Observed Mix (%)": [50, 30, 20],
        "Retention (%)": [75, 85, 95] # Different rates for different tiers
    }
    
    df = pd.DataFrame(default_data)
    
    # Configure the columns dynamically based on the checkbox
    cols_config = {
        "Year 1 Price ($)": st.column_config.NumberColumn(format="$%d", help="Price paid at signup"),
        "Year 2 Price ($)": st.column_config.NumberColumn(format="$%d", help="Price paid at renewal"),
        "Observed Mix (%)": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=100, help="Distribution of sales"),
        "Retention (%)": st.column_config.NumberColumn(format="%d%%", min_value=0, max_value=100, help="% of users who renew Year 2")
    }
    
    # If advanced is OFF, we hide the Retention column to keep it simple
    if not show_advanced:
        column_order = ["Policy Name", "Year 1 Price ($)", "Year 2 Price ($)", "Observed Mix (%)"]
        df["Retention (%)"] = global_retention * 100
    else:
        column_order = ["Policy Name", "Year 1 Price ($)", "Year 2 Price ($)", "Observed Mix (%)", "Retention (%)"]

    edited_df = st.data_editor(
        df,
        column_config=cols_config,
        column_order=column_order,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )
    
    if show_advanced:
        st.caption("💡 **Tip:** You can copy-paste directly from Excel into this table.")

# --- BACKEND MATH (WEIGHTED AVERAGES) ---
total_mix = edited_df["Observed Mix (%)"].sum()
if total_mix == 0: st.stop()

# Normalize weights
edited_df["Weight"] = edited_df["Observed Mix (%)"] / total_mix

# Calculate LTV PER ROW first
edited_df["Row LTV"] = edited_df["Year 1 Price ($)"] + \
                       (edited_df["Year 2 Price ($)"] * (edited_df["Retention (%)"]/100))

# Blended LTV is the weighted average of the Row LTVs
blended_ltv = (edited_df["Row LTV"] * edited_df["Weight"]).sum()

# We also calculate "Effective Retention" just for the simulation volatility later
effective_retention = (edited_df["Retention (%)"] * edited_df["Weight"]).sum() / 100.0

with col_summ:
    st.markdown("**Unit Economics (Average Customer)**")
    st.write("Based on your pricing and mix:")
    st.metric("Blended Lifetime Value (LTV)", f"${blended_ltv:.2f}", 
             help="The weighted average value of one policy sold, including Year 1 + Year 2.")
    
    if show_advanced:
         st.caption(f"Effective Portfolio Retention: **{effective_retention*100:.1f}%**")

# --- SECTION 2: PERFORMANCE & BREAK-EVEN ---
st.divider()
st.header("2. Performance & Financials")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("#### 🅰️ Baseline Strategy")
    cv_control = st.number_input("Current Conversion Rate (%)", value=2.0, format="%.2f", 
                                help="What is your current conversion rate?") / 100
    current_rev = traffic * cv_control * blended_ltv

with c2:
    st.markdown("#### 🅱️ New Strategy")
    cv_variant = st.number_input("New Conversion Rate (%)", value=2.3, format="%.2f",
                                help="What conversion rate did the A/B test achieve?") / 100
    new_rev = traffic * cv_variant * blended_ltv

# --- BREAK EVEN LOGIC ---
be_revenue_target = current_rev + cost
be_cr = be_revenue_target / (traffic * blended_ltv) if (traffic * blended_ltv) > 0 else 0
be_lift_needed = (be_cr - cv_control) / cv_control

with c3:
    st.markdown("#### 🎯 The Target")
    if be_cr > 1.0:
        st.error("Cost is too high. Impossible to break even.")
    else:
        color = "green" if cv_variant >= be_cr else "red"
        st.markdown(f"To pay back the **${cost:,}** cost, you *must* hit:")
        st.metric(
            label="Break-Even Conversion Rate", 
            value=f"{be_cr*100:.2f}%", 
            delta=f"{be_lift_needed:.1%} lift required",
            delta_color="inverse",
            help="If your New Strategy is below this number, you are losing money."
        )

# --- SECTION 3: EXECUTIVE SUMMARY ---
st.divider()
inc_revenue = new_rev - current_rev
roi = ((inc_revenue - cost) / cost) * 100 if cost > 0 else 0

st.subheader("🚀 Executive Summary")

# Smart Text Generation
if roi > 0:
    outcome_msg = f"✅ **Green Light:** This strategy is projected to generate **${inc_revenue - cost:,.0f}** in pure profit."
    outcome_color = "success"
else:
    outcome_msg = f"⚠️ **Caution:** This strategy is projected to **lose ${abs(inc_revenue - cost):,.0f}**. The lift in conversion does not cover the implementation costs."
    outcome_color = "error"

if outcome_color == "success":
    st.success(outcome_msg)
else:
    st.error(outcome_msg)

m1, m2, m3 = st.columns(3)
m1.metric("Incremental Revenue (Top Line)", f"${inc_revenue:,.0f}", help="Total extra cash generated over 2 years vs the old strategy.")
m2.metric("Return on Investment (ROI)", f"{roi:.0f}%", help="For every $1 spent on the project, what % do you get back?")
m3.metric("Net Profit (Bottom Line)", f"${inc_revenue - cost:,.0f}", help="Revenue minus Project Costs.")

# --- SECTION 4: RISK SIMULATOR (MONTE CARLO) ---
st.divider()
st.header("🎲 Risk & Confidence Analysis")
st.markdown("""
**Why run this?** Your inputs (Conversion Rate, Retention) are estimates. 
This tool simulates **1,000 different futures** where these numbers vary slightly (±10%) to see if the strategy is *robust*.
""")

if st.button("Run Risk Simulation", type="primary"):
    
    with st.spinner("Crunching 1,000 scenarios..."):
        # SIMULATION SETTINGS
        simulations = 1000
        volatility = 0.10 
        
        # 1. Randomize Conversion Rates
        sim_cv_variant = np.random.normal(cv_variant, cv_variant * volatility, simulations)
        
        # 2. Randomize LTV (via Retention)
        avg_price_y1 = (edited_df["Year 1 Price ($)"] * edited_df["Weight"]).sum()
        avg_price_y2 = (edited_df["Year 2 Price ($)"] * edited_df["Weight"]).sum()
        
        sim_retention = np.random.normal(effective_retention, effective_retention * (volatility/2), simulations)
        sim_retention = np.clip(sim_retention, 0.1, 1.0) 
        
        sim_ltv = avg_price_y1 + (sim_retention * avg_price_y2)
        
        # 3. Outcomes
        sim_rev_variant = traffic * sim_cv_variant * sim_ltv
        
        # Baseline Variation
        sim_cv_control = np.random.normal(cv_control, cv_control * (volatility/2), simulations)
        sim_rev_control = traffic * sim_cv_control * blended_ltv 
        
        sim_inc_profit = (sim_rev_variant - sim_rev_control) - cost
        
        # METRICS
        wins = np.sum(sim_inc_profit > 0)
        win_rate = (wins / simulations) * 100
        
        # VISUALIZATION
        col_risk_metrics, col_risk_chart = st.columns([1, 2])
        
        with col_risk_metrics:
            st.markdown(f"### Probability of Profit: :blue[{win_rate:.1f}%]")
            
            if win_rate > 80:
                st.success("Safe Bet. Highly likely to make money.")
            elif win_rate > 50:
                st.warning("Moderate Risk. It's a coin flip.")
            else:
                st.error("High Risk. Likely to lose money.")
                
            st.write(f"**Best Case:** ${np.percentile(sim_inc_profit, 95):,.0f}")
            st.write(f"**Worst Case:** ${np.percentile(sim_inc_profit, 5):,.0f}")
            
        with col_risk_chart:
            fig = px.histogram(
                x=sim_inc_profit, 
                nbins=30,
                color_discrete_sequence=['#00CC96'],
                title="Profit/Loss Distribution (1,000 Scenarios)"
            )
            fig.add_vline(x=0, line_width=3, line_dash="dash", line_color="red", annotation_text="Break Even")
            fig.update_layout(xaxis_title="Net Profit ($)", yaxis_title="Scenarios", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
