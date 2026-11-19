from datetime import datetime
from io import StringIO
import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import (
    D,
    aggregate_ledger_horizon,
    check_balance_sheet,
    compute_derived_capacity,
    compute_fixed_cost,
    compute_unit_costs,
    create_initial_state,
    precalc_average_cost,
    precalc_composed_profit,
    precalc_growth_target,
    precalc_seasonal_demand,
    run_monthly_step,
    validate_and_import_snapshot,
)

st.set_page_config(
    page_title="Career Venture Lab | ROB-2 Precalculus Studio",
    page_icon="🤖",
    layout="wide",
)

DEFAULT_FIXTURE_CSV = """month,requested,capacity_override,ad_cost
2027-01,40,30,0
2027-02,44,30,100
2027-03,36,22,0
"""

if "sim_state" not in st.session_state:
    st.session_state.sim_state = create_initial_state()

state = st.session_state.sim_state

# --- Sidebar: Global Governance, Mode & Persistence ---
with st.sidebar:
    st.header("🤖 ROB-2 Governance & State")
    team_id_input = st.text_input("Team ID", value=state["team_id"])
    if team_id_input != state["team_id"]:
        state["team_id"] = team_id_input

    st.caption(
        f"**Course:** {state['course']} | **Pathway:** {state['pathway_id']} | "
        f"**Snapshot:** `{state['snapshot_id']}` (v{state['state_version']})"
    )

    st.divider()
    st.subheader("Math Challenge Level")
    levels = ["Foundation", "Applied", "Advanced"]
    chosen_level = st.selectbox(
        "Approved Precalculus Level",
        options=levels,
        index=levels.index(state["selected_level"]),
        help="Changing levels changes equations, controls, visuals, and interpretation tasks.",
    )
    teacher_approved = st.checkbox(
        "Teacher approved this challenge level",
        value=state.get("level_approved_by_teacher", True),
    )
    if chosen_level != state["selected_level"]:
        if teacher_approved:
            state["selected_level"] = chosen_level
            for k in state["level_by_skill"]:
                state["level_by_skill"][k] = chosen_level
            st.success(f"Challenge level switched to {chosen_level}.")
        else:
            st.warning("Check 'Teacher approved this challenge level' before switching.")

    if state["selected_level"] == "Advanced":
        ext_choice = st.radio(
            "Advanced Extension (select ONE)",
            options=["Seasonal Trigonometric", "Exponential / Logarithmic Growth"],
            index=0 if state.get("advanced_extension") == "Seasonal Trigonometric" else 1,
        )
        state["advanced_extension"] = ext_choice

    st.divider()
    st.subheader("Durable Save / Restore (JSON)")
    st.info("Browser session state and Render files are ephemeral. Download JSON to save progress.")
    snapshot_bytes = json.dumps(state, indent=2).encode("utf-8")
    st.download_button(
        label="⬇️ Export Approved Snapshot (.json)",
        data=snapshot_bytes,
        file_name=f"{state['team_id']}_{state['pathway_id']}_v{state['state_version']}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded_json = st.file_uploader("Restore / Import Snapshot (.json)", type=["json"])
    if uploaded_json is not None:
        if st.button("Validate & Import JSON", use_container_width=True):
            raw_text = uploaded_json.read().decode("utf-8")
            ok, msg, restored = validate_and_import_snapshot(
                raw_text,
                expected_team_id=state["team_id"],
                current_version=int(state["state_version"]),
            )
            if ok and restored is not None:
                st.session_state.sim_state = restored
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.divider()
    if st.button("🔄 Reset to Post-Startup State ($5,000 Cash, 100 Kits)", use_container_width=True):
        st.session_state.sim_state = create_initial_state(
            team_id=state["team_id"],
            selected_level=state["selected_level"],
            advanced_extension=state.get("advanced_extension", "Seasonal Trigonometric"),
        )
        st.success("Reset to post-startup baseline.")
        st.rerun()

# --- Header & Persistent Math Skills Banner ---
st.title("Robotics Kit & Repair Studio (`ROB-2` | Precalculus)")
st.caption(
    "Stage 1 Build: Deterministic Ledger, Robotics Inventory/Defect Engine, Precalculus Function Lab & Fixture Verification. "
    "Simulation only — fictional business assumptions."
)

comp_unit, noncomp_unit, total_var_unit = compute_unit_costs(state)
fixed_monthly = compute_fixed_cost(state)
derived_cap = compute_derived_capacity(state)
bal = check_balance_sheet(state)

with st.container(border=True):
    m_col1, m_col2, m_col3 = st.columns([2, 3, 2])
    with m_col1:
        st.markdown("### 📐 Persistent Math Panel")
        st.markdown(
            f"**Course:** Precalculus (`ROB-2`)  \n"
            f"**Approved Level:** `{state['selected_level']}`  \n"
            f"**Active Capacity:** `{derived_cap}` kits/mo (`floor({state['parameters']['staff_hours']}/{state['parameters']['hours_per_unit']})`)"
        )
    with m_col2:
        if state["selected_level"] == "Foundation":
            st.markdown(
                "**Skill:** Rational Average Cost Function  \n"
                "**Equation:** $A(s) = \\frac{F}{s} + v = \\frac{"
                f"{float(fixed_monthly):.0f}"
                "}{s} + "
                f"{float(total_var_unit):.2f}$  \n"
                f"**Domain & Asymptotes:** $0 < s \\le {derived_cap}$ kits; Vertical asymptote $s=0$ ($A(0)$ undefined); Horizontal asymptote $y = \\${float(total_var_unit):.2f}$."
            )
        elif state["selected_level"] == "Applied":
            bp = float(D(state["parameters"]["base_price"])) * (2.0 - derived_cap / float(state["parameters"]["D0"]))
            st.markdown(
                "**Skill:** Function Composition & Piecewise Profit  \n"
                "**Equations:** $q(p) = \\max(0, 2D_0 - \\frac{D_0}{p_0}p)$, $s(p) = \\min(\\text{cap}, q(p))$, $P(p) = p\\cdot s(p) - (F + v\\cdot s(p))$  \n"
                f"**Domain & Breakpoint:** $0 \\le p \\le \\${2*float(D(state['parameters']['base_price'])):.0f}$; Capacity breakpoint at $p = \\${bp:.2f}$."
            )
        else:
            if state.get("advanced_extension") == "Seasonal Trigonometric":
                st.markdown(
                    "**Skill:** Periodic Seasonal Demand Modeling  \n"
                    "**Equation:** $D(t) = D_0\\left(1 + 0.20\\sin\\left(\\frac{2\\pi(t-1)}{12}\\right)\\right)$, Realized $s(t) = \\min(\\text{cap}, D(t))$  \n"
                    f"**Domain:** Month $t \\in [1, 12]$ (12-mo period; peak $t=4$, trough $t=10$; clipped at capacity `{derived_cap}`)."
                )
            else:
                st.markdown(
                    "**Skill:** Exponential Growth & Logarithmic Target Solver  \n"
                    "**Equation:** $D(t) = D_0(1 + r)^{t-1}$, Target month $t = 1 + \\frac{\\ln(D_{\\text{target}}/D_0)}{\\ln(1+r)}$  \n"
                    f"**Domain:** $t \\ge 1$, growth rate $r > 0$; realized sales clipped at capacity `{derived_cap}`."
                )
    with m_col3:
        st.markdown("**Business Question & Transfer Check**")
        st.caption(
            "How do assembly hours, component inventory, and pricing constraints bound feasible profit? "
            "Predict the effect of a parameter change BEFORE moving a slider in the Math Lab."
        )

# --- Main Tabs ---
tab_overview, tab_inputs, tab_math, tab_ledger = st.tabs(
    [
        "1. Overview & System Map",
        "2. Inputs, Funding & Monthly Step",
        "3. Precalculus Math Lab (ROB-2)",
        "4. Ledger & Fixture Verification",
    ]
)

# ==============================================================================
# TAB 1: OVERVIEW & SYSTEM MAP
# ==============================================================================
with tab_overview:
    st.subheader("Current Reconciled Financial & Inventory Position")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Spendable Cash", f"${bal['cash']:,.2f}")
    k2.metric(
        "Component Inventory",
        f"{state['balances']['inventory_units']} sets",
        delta=f"Value: ${bal['inventory_value']:,.2f}",
        delta_color="off",
    )
    k3.metric("Equipment (Net)", f"${bal['equipment_net']:,.2f}")
    k4.metric("Debt Principal", f"${bal['debt_principal']:,.2f}")
    k5.metric("Retained Earnings", f"${bal['retained_earnings']:,.2f}")

    if bal["reconciled"]:
        st.success(
            f"✅ Balance Sheet Reconciled: Total Assets (${bal['total_assets']:,.2f}) = "
            f"Liabilities (${bal['debt_principal']:,.2f}) + Equity (${bal['total_equity']:,.2f})"
        )
    else:
        st.error(f"❌ Balance Sheet Out of Balance by ${bal['difference']:,.2f}")

    st.divider()
    col_sys, col_roadmap = st.columns([3, 2])
    with col_sys:
        st.subheader("System Dependency Map & Feedback Loop")
        st.markdown(
            """
            ```text
            [Marketing Studio (Student-Approved Campaign)]
                   │ (campaign_id, itemized ad_cost)
                   ▼
            [Demand Model q(p) / D(t) (Deterministic Engine)]
                   │ (requested kits)
                   ▼
            [Operations Fulfillment (Deterministic Engine)] ◄── [Component Stock & Staff Hours]
                   │ attempted = min(requested, capacity, stock)
                   │ failed = floor(attempted * defect_rate)
                   │ sold = attempted - failed
                   ▼
            [Dated Event Ledger & Financial Balances (Student-Approved Step)]
                   │
                   └──► Feedback Loop: Quality / Defect Rate & Fulfillment Rate ──► Future Demand
            ```
            - **Automatic (Deterministic Code):** Capacity math, inventory consumption, `Decimal` ledger entries, and Precalculus curves.
            - **Student-Managed:** Approving inputs, reviewing AI proposals (`pending` -> `approved`), executing one simulation step, and verifying math.
            """
        )
    with col_roadmap:
        st.subheader("Build Roadmap Status")
        st.markdown(
            """
            - **Stage 1 (Active):** Startup balances, editable cost rows, Robotics inventory/defect rules, Precalculus Math Lab (`Foundation`/`Applied`/`Advanced`), dated ledger, JSON Save/Restore, and `monthly_fixture.csv` tests.
            - **Stage 2 (Not Yet Implemented):** Departmental AI review cards (`Finance`, `Operations`, `Market/Marketing`, `Reviewer`), full 8-report PDF Center, costed Marketing Studio.
            - **Stage 3 (Not Yet Implemented):** Frozen-snapshot Practice Assessment generator & Cross-Course sensor/defect artifact panel.
            - **Stage 4 (Optional, Lowest Priority):** Demonstration storefront with fictional checkout tokens.
            """
        )

# ==============================================================================
# TAB 2: INPUTS, FUNDING & MONTHLY STEP
# ==============================================================================
with tab_inputs:
    st.subheader("Editable Parameters & Cost Structure (Fictional Teaching Defaults)")
    c_param, c_var, c_fix = st.columns(3)

    with c_param:
        st.markdown("**Operating & Pricing Parameters**")
        new_price = st.number_input("Base Price ($/kit)", min_value=1.0, value=float(D(state["parameters"]["base_price"])), step=5.0)
        new_d0 = st.number_input("Baseline Demand D0 (kits/mo)", min_value=0, value=int(state["parameters"]["D0"]), step=1)
        new_hours = st.number_input("Productive Staff Hours / Month", min_value=0.0, value=float(state["parameters"]["staff_hours"]), step=3.0)
        new_hpu = st.number_input("Assembly Hours / Kit", min_value=0.25, value=float(state["parameters"]["hours_per_unit"]), step=0.25)
        new_defect = st.slider("Defect Rate (0.00 to 1.00)", min_value=0.0, max_value=1.0, value=float(state["parameters"]["defect_rate"]), step=0.01)

    with c_var:
        st.markdown("**Per-Attempted-Unit Variable Costs ($/kit)**")
        v_comp = st.number_input("Components COGS ($/kit)", min_value=0.0, value=float(D(state["variable_cost_lines"]["components_COGS"])), step=1.5)
        v_labor = st.number_input("Assembly Labor ($/kit)", min_value=0.0, value=float(D(state["variable_cost_lines"]["assembly_labor"])), step=1.0)
        v_pack = st.number_input("Packaging ($/kit)", min_value=0.0, value=float(D(state["variable_cost_lines"]["packaging"])), step=1.0)
        v_warr = st.number_input("Warranty Consumables ($/kit)", min_value=0.0, value=float(D(state["variable_cost_lines"]["warranty_consumables"])), step=1.0)
        st.info(f"Total Variable Cost: **${v_comp + v_labor + v_pack + v_warr:.2f} / attempted kit**")

    with c_fix:
        st.markdown("**Monthly Fixed Expenses ($/month)**")
        f_work = st.number_input("Workspace ($/mo)", min_value=0.0, value=float(D(state["fixed_cost_lines"]["workspace"])), step=10.0)
        f_soft = st.number_input("Software ($/mo)", min_value=0.0, value=float(D(state["fixed_cost_lines"]["software"])), step=10.0)
        f_maint = st.number_input("Equipment Maintenance ($/mo)", min_value=0.0, value=float(D(state["fixed_cost_lines"]["equipment_maintenance"])), step=10.0)
        f_admin = st.number_input("Admin ($/mo)", min_value=0.0, value=float(D(state["fixed_cost_lines"]["admin"])), step=10.0)
        st.info(f"Total Fixed Expense: **${f_work + f_soft + f_maint + f_admin:.2f} / month**")

    if st.button("💾 Apply Parameter & Cost Updates (Scenario/Setup)", use_container_width=True):
        state["parameters"]["base_price"] = str(D(new_price))
        state["parameters"]["D0"] = int(new_d0)
        state["parameters"]["staff_hours"] = float(new_hours)
        state["parameters"]["hours_per_unit"] = float(new_hpu)
        state["parameters"]["defect_rate"] = float(new_defect)
        state["parameters"]["component_unit_cost"] = str(D(v_comp))
        state["variable_cost_lines"] = {
            "components_COGS": str(D(v_comp)),
            "assembly_labor": str(D(v_labor)),
            "packaging": str(D(v_pack)),
            "warranty_consumables": str(D(v_warr)),
        }
        state["fixed_cost_lines"] = {
            "workspace": str(D(f_work)),
            "software": str(D(f_soft)),
            "equipment_maintenance": str(D(f_maint)),
            "admin": str(D(f_admin)),
        }
        state["capacity"]["staff_hours"] = float(new_hours)
        state["capacity"]["hours_per_unit"] = float(new_hpu)
        state["capacity"]["derived_capacity"] = compute_derived_capacity(state)
        st.success("Parameters and cost rows updated. Advance a monthly step below to record transactions.")
        st.rerun()

    st.divider()
    st.subheader("Advance Simulation One Month (Normal Mode)")
    with st.form("advance_month_form"):
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            run_id_in = st.text_input("Unique Run ID", value=f"RUN-{state['state_version']:03d}")
            sim_date_in = st.text_input("Month-End Date (YYYY-MM-DD)", value="2027-01-31")
        with s2:
            req_in = st.number_input("Requested Demand (kits)", min_value=0, value=int(state["parameters"]["D0"]), step=1)
            step_price_in = st.number_input("Selling Price ($/kit)", min_value=0.0, value=float(D(state["parameters"]["base_price"])), step=5.0)
        with s3:
            restock_in = st.number_input("Component Restock (sets purchased)", min_value=0, value=0, step=5)
            ad_in = st.number_input("Approved Marketing Expense ($)", min_value=0.0, value=0.0, step=25.0)
            camp_id_in = st.text_input("Campaign ID (if ad > 0)", value="")
        with s4:
            loan_in = st.number_input("New Loan Received ($)", min_value=0.0, value=0.0, step=100.0)
            repay_in = st.number_input("Loan Principal Repaid ($)", min_value=0.0, value=0.0, step=100.0)
            interest_in = st.number_input("Loan Interest Expense ($)", min_value=0.0, value=0.0, step=10.0)
            capex_in = st.number_input("Equipment Purchase CapEx ($)", min_value=0.0, value=0.0, step=100.0)

        prediction_in = st.text_input(
            "Student Transfer Prediction (Required: predict sold units, profit, and cash change before running)",
            placeholder="e.g., Capacity 30 caps demand 40; sold=30, revenue=$3,600, profit=$1,050, cash rises $1,950.",
        )
        submitted = st.form_submit_button("✅ Approve & Advance Simulation One Month", use_container_width=True)
        if submitted:
            ok, msg, updated = run_monthly_step(
                state=state,
                run_id=run_id_in.strip(),
                sim_date=sim_date_in.strip(),
                requested=int(req_in),
                unit_price=D(step_price_in),
                restock_units=int(restock_in),
                ad_cost=D(ad_in),
                campaign_id=camp_id_in.strip() or None,
                loan_cash=D(loan_in),
                principal_repayment=D(repay_in),
                interest_expense=D(interest_in),
                additional_capex=D(capex_in),
                student_prediction=prediction_in.strip(),
            )
            if ok:
                st.session_state.sim_state = updated
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ==============================================================================
# TAB 3: PRECALCULUS MATH LAB (ROB-2)
# ==============================================================================
with tab_math:
    st.subheader(f"Precalculus Math Lab — Level: {state['selected_level']} (`ROB-2`)")
    F_val = float(fixed_monthly)
    v_val = float(total_var_unit)
    p0_val = float(D(state["parameters"]["base_price"]))
    D0_val = float(state["parameters"]["D0"])
    cap_val = int(derived_cap)

    # --- LEVEL 1: FOUNDATION (Rational Average Cost) ---
    if state["selected_level"] == "Foundation":
        st.markdown(
            f"**Model:** Total Cost $C(s) = {F_val:.2f} + {v_val:.2f}s$ and Average Cost "
            f"$A(s) = \\frac{{{F_val:.2f}}}{{s}} + {v_val:.2f}$ on practical domain $0 < s \\le {cap_val}$ kits."
        )
        s_inspect = st.slider("Inspect Quantity $s$ (kits/month)", min_value=0, max_value=max(1, cap_val), value=min(15, max(1, cap_val)))
        a_val = precalc_average_cost(s_inspect, F_val, v_val)
        if a_val is None:
            st.error("At $s = 0$, $A(0)$ is **UNDEFINED** (vertical asymptote at $s = 0$; fixed cost cannot be divided across zero kits).")
        else:
            st.info(
                f"At $s = {s_inspect}$ kits: Total Cost $C({s_inspect}) = \\${F_val + v_val * s_inspect:,.2f}$ | "
                f"Average Cost $A({s_inspect}) = \\${a_val:,.2f}$ per kit | Horizontal Asymptote: $y = \\${v_val:,.2f}$ per kit."
            )

        s_grid = list(range(1, max(2, cap_val + 1)))
        export_df = pd.DataFrame(
            {
                "Quantity s (kits)": s_grid,
                "Total Cost C(s) ($)": [round(F_val + v_val * s, 2) for s in s_grid],
                "Average Cost A(s) ($/kit)": [round(precalc_average_cost(s, F_val, v_val), 2) for s in s_grid],
                "Horizontal Asymptote ($/kit)": [round(v_val, 2) for _ in s_grid],
            }
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=export_df["Quantity s (kits)"],
                y=export_df["Average Cost A(s) ($/kit)"],
                mode="lines+markers",
                name="Average Cost A(s) ($/kit)",
                line=dict(width=3),
                marker=dict(symbol="circle", size=7),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=export_df["Quantity s (kits)"],
                y=export_df["Horizontal Asymptote ($/kit)"],
                mode="lines",
                name=f"Horizontal Asymptote y = ${v_val:.2f}",
                line=dict(dash="dash", width=2),
            )
        )
        fig.add_vline(x=0, line_dash="dot", annotation_text="Vertical Asymptote s=0 (Undefined)")
        fig.add_vline(x=cap_val, line_dash="dashdot", annotation_text=f"Capacity Limit s={cap_val}")
        fig.update_layout(
            title=f"PROJECTED: Average Cost Curve A(s) | Snapshot {state['snapshot_id']} (Domain: 0 < s <= {cap_val})",
            xaxis_title="Completed Kits s (units/month)",
            yaxis_title="Cost per Kit ($/kit)",
            yaxis=dict(rangemode="tozero"),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(export_df, use_container_width=True, hide_index=True)

    # --- LEVEL 2: APPLIED (Function Composition & Piecewise Profit) ---
    elif state["selected_level"] == "Applied":
        bp = p0_val * (2.0 - cap_val / D0_val) if D0_val > 0 else 0.0
        st.markdown(
            f"**Composed Pipeline:** Price $p$ $\\rightarrow$ Demand $q(p) = \\max(0, {2*D0_val:.0f} - \\frac{{{D0_val:.0f}}}{{{p0_val:.0f}}}p)$ "
            f"$\\rightarrow$ Sales $s(p) = \\min({cap_val}, q(p))$ $\\rightarrow$ Profit $P(p) = p\\cdot s(p) - ({F_val:.0f} + {v_val:.2f}s(p))$ "
            f"on domain $0 \\le p \\le \\${2*p0_val:.0f}$. Capacity breakpoint occurs at **$p = \\${bp:.2f}$**."
        )
        p_inspect = st.slider("Inspect Kit Price $p$ ($/kit)", min_value=0.0, max_value=float(2 * p0_val), value=float(p0_val), step=5.0)
        res = precalc_composed_profit(p_inspect, D0_val, p0_val, cap_val, F_val, v_val)
        st.info(
            f"At $p = \\${p_inspect:.2f}$: Unconstrained Demand $q(p) = {res['demand_q_cont']:.2f}$ kits | "
            f"Continuous Sales $s(p) = {res['sales_s_cont']:.2f}$ (Continuous Profit: **\\${res['profit_cont']:,.2f}**) | "
            f"Integer Ledger Sales $\\lfloor s(p) \\rfloor = {int(res['sales_s_int'])}$ (Integer Profit: **\\${res['profit_int']:,.2f}**)."
        )

        prices = [float(p) for p in range(0, int(2 * p0_val) + 1, 10)]
        rows = [precalc_composed_profit(p, D0_val, p0_val, cap_val, F_val, v_val) for p in prices]
        export_df = pd.DataFrame(rows)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=export_df["price_p"],
                y=export_df["profit_cont"],
                mode="lines+markers",
                name="Continuous Profit P(p) ($)",
                line=dict(width=3),
                marker=dict(symbol="circle"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=export_df["price_p"],
                y=export_df["profit_int"],
                mode="lines+markers",
                name="Integer-Floored Profit ($)",
                line=dict(dash="dash", width=2),
                marker=dict(symbol="square"),
            )
        )
        fig.add_hline(y=0, line_dash="dot", annotation_text="Break-Even Zero Line ($0)")
        if 0 <= bp <= 2 * p0_val:
            fig.add_vline(x=bp, line_dash="dashdot", annotation_text=f"Capacity Breakpoint p=${bp:.2f}")
        fig.update_layout(
            title=f"PROJECTED: Composed Profit P(p) vs. Price | Snapshot {state['snapshot_id']}",
            xaxis_title="Unit Price p ($/kit)",
            yaxis_title="Monthly Operating Profit ($)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(export_df.round(2), use_container_width=True, hide_index=True)

    # --- LEVEL 3: ADVANCED (Seasonal Trig OR Exponential/Log Target) ---
    else:
        if state.get("advanced_extension") == "Seasonal Trigonometric":
            st.markdown(
                f"**Seasonal Trigonometric Model (Assumed Seasonality):** "
                f"$D(t) = {D0_val:.0f}\\left(1 + 0.20\\sin\\left(\\frac{{2\\pi(t-1)}}{{12}}\\right)\\right)$ for month $t \\in [1, 12]$, "
                f"clipped at capacity $s(t) = \\min({cap_val}, D(t))$. Peak at $t=4$ ($1.20 D_0 = {1.2*D0_val:.1f}$ kits); "
                f"trough at $t=10$ ($0.80 D_0 = {0.8*D0_val:.1f}$ kits)."
            )
            months = list(range(1, 13))
            s_rows = [precalc_seasonal_demand(t, D0_val, cap_val) for t in months]
            export_df = pd.DataFrame(s_rows)
            export_df["projected_profit_int ($)"] = export_df["sales_clipped_int"] * (p0_val - v_val) - F_val

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=export_df["month_t"],
                    y=export_df["demand_raw"],
                    mode="lines+markers",
                    name="Unconstrained Seasonal Demand D(t)",
                    line=dict(width=3),
                    marker=dict(symbol="circle", size=8),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=export_df["month_t"],
                    y=export_df["sales_clipped_int"],
                    mode="lines+markers",
                    name="Realized Integer Sales s(t) (Capacity-Clipped)",
                    line=dict(dash="dash", width=3),
                    marker=dict(symbol="diamond", size=8),
                )
            )
            fig.add_hline(y=cap_val, line_dash="dot", annotation_text=f"Capacity Ceiling ({cap_val} kits)")
            fig.update_layout(
                title=f"PROJECTED SEASONALITY: Demand D(t) vs. Capacity-Clipped Sales | Snapshot {state['snapshot_id']}",
                xaxis_title="Month Index t (1 to 12)",
                yaxis_title="Kits per Month",
                yaxis=dict(rangemode="tozero"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(export_df.round(2), use_container_width=True, hide_index=True)
        else:
            c_g1, c_g2 = st.columns(2)
            r_rate = c_g1.slider("Assumed Monthly Demand Growth Rate r", min_value=0.01, max_value=0.25, value=0.05, step=0.01)
            target_d = c_g2.number_input("Target Monthly Demand (kits)", min_value=int(D0_val) + 1, value=60, step=5)
            months = list(range(1, 13))
            g_rows = [precalc_growth_target(t, D0_val, r_rate, float(target_d), cap_val) for t in months]
            export_df = pd.DataFrame(g_rows)
            t_hit = g_rows[0]["months_to_target"]
            st.info(
                f"Exponential Model $D(t) = {D0_val:.0f}(1 + {r_rate:.2f})^{{t-1}}$ reaches target demand "
                f"**{target_d} kits** at **$t = {t_hit:.2f}$ months** (unless capacity `{cap_val}` is expanded first). "
                "Extrapolation beyond 12 months is unreliable without staffing/inventory expansion."
            )
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=export_df["month_t"],
                    y=export_df["demand_raw"],
                    mode="lines+markers",
                    name="Projected Demand D(t)",
                    line=dict(width=3),
                    marker=dict(symbol="circle"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=export_df["month_t"],
                    y=export_df["sales_clipped_int"],
                    mode="lines+markers",
                    name="Realized Integer Sales s(t)",
                    line=dict(dash="dash", width=3),
                    marker=dict(symbol="square"),
                )
            )
            fig.add_hline(y=cap_val, line_dash="dot", annotation_text=f"Capacity Ceiling ({cap_val} kits)")
            fig.update_layout(
                title=f"PROJECTED GROWTH: D(t) vs. Capacity Ceiling | Snapshot {state['snapshot_id']}",
                xaxis_title="Month Index t",
                yaxis_title="Kits per Month",
                yaxis=dict(rangemode="tozero"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(export_df.round(2), use_container_width=True, hide_index=True)

    meta_comment = (
        f"# Team: {state['team_id']} | Pathway: {state['pathway_id']} | Level: {state['selected_level']} | "
        f"Snapshot: {state['snapshot_id']} | Status: PROJECTED MODEL | Exported: {datetime.now().isoformat()}\n"
    )
    csv_export = meta_comment + export_df.to_csv(index=False)
    st.download_button(
        "⬇️ Download Linked Chart Data & Provenance (.csv)",
        data=csv_export.encode("utf-8"),
        file_name=f"{state['team_id']}_{state['pathway_id']}_{state['selected_level']}_math_table.csv",
        mime="text/csv",
    )

# ==============================================================================
# TAB 4: LEDGER & FIXTURE VERIFICATION
# ==============================================================================
with tab_ledger:
    st.subheader("Dated Event Ledger & Time-Horizon Views")
    horizon = st.radio(
        "Select Aggregation Horizon",
        options=[
            "Monthly (Observed Ledger)",
            "Yearly (Aggregated Ledger)",
            "Daily (Modeled Allocation)",
        ],
        horizontal=True,
    )
    if horizon == "Daily (Modeled Allocation)":
        st.warning(
            f"Daily figures are modeled allocations (`monthly / {state['working_days']} working days`), "
            "NOT observed daily sales transactions."
        )

    agg_rows = aggregate_ledger_horizon(state["ledger"], horizon, working_days=int(state["working_days"]))
    if agg_rows:
        df_led = pd.DataFrame(agg_rows)
        st.dataframe(df_led, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Export Ledger View (.csv)",
            data=df_led.to_csv(index=False).encode("utf-8"),
            file_name=f"{state['team_id']}_{state['pathway_id']}_ledger_{state['snapshot_id']}.csv",
            mime="text/csv",
        )
    else:
        st.info("No transactions recorded yet. Advance a month in Tab 2 or run the Fixture Replay below.")

    st.divider()
    st.subheader("ROB Package Acceptance Fixture Replay (`monthly_fixture.csv`)")
    st.warning(
        "Fixture-Test Mode uses explicit `capacity_override` values (30, 30, 22) solely to verify ledger accounting "
        "against handbook expectations. It resets the simulation to post-startup baseline first."
    )
    if st.button("▶️ Run Official ROB 3-Month Fixture & Edge-Case Verification", use_container_width=True):
        test_state = create_initial_state(
            team_id=state["team_id"],
            selected_level=state["selected_level"],
            advanced_extension=state.get("advanced_extension", "Seasonal Trigonometric"),
        )
        fixture_path = "sample_data/monthly_fixture.csv"
        if os.path.exists(fixture_path):
            fixture_df = pd.read_csv(fixture_path)
        else:
            fixture_df = pd.read_csv(StringIO(DEFAULT_FIXTURE_CSV))

        expected = [
            {"month": "2027-01", "sold": 30, "rev": D("3600.00"), "exp": D("2550.00"), "prof": D("1050.00"), "cash": D("6950.00"), "stock": 70},
            {"month": "2027-02", "sold": 30, "rev": D("3600.00"), "exp": D("2650.00"), "prof": D("950.00"), "cash": D("8800.00"), "stock": 40},
            {"month": "2027-03", "sold": 22, "rev": D("2640.00"), "exp": D("2030.00"), "prof": D("610.00"), "cash": D("10070.00"), "stock": 18},
        ]
        results_table = []
        all_passed = True
        for idx, row in fixture_df.iterrows():
            m = str(row["month"])
            ok, msg, test_state = run_monthly_step(
                state=test_state,
                run_id=f"FIX-{m}",
                sim_date=f"{m}-28",
                requested=int(row["requested"]),
                capacity_override=int(row["capacity_override"]),
                ad_cost=D(row["ad_cost"]),
            )
            entry = test_state["ledger"][-1]
            exp = expected[idx]
            row_pass = (
                ok
                and entry["sold"] == exp["sold"]
                and D(entry["net_revenue"]) == exp["rev"]
                and D(entry["total_operating_expense"]) == exp["exp"]
                and D(entry["operating_profit"]) == exp["prof"]
                and D(entry["closing_cash"]) == exp["cash"]
                and entry["ending_stock"] == exp["stock"]
                and check_balance_sheet(test_state)["reconciled"]
            )
            all_passed = all_passed and row_pass
            results_table.append(
                {
                    "Month": m,
                    "Sold (Exp/Act)": f"{exp['sold']} / {entry['sold']}",
                    "Revenue (Exp/Act)": f"${exp['rev']} / ${entry['net_revenue']}",
                    "Expense (Exp/Act)": f"${exp['exp']} / ${entry['total_operating_expense']}",
                    "Profit (Exp/Act)": f"${exp['prof']} / ${entry['operating_profit']}",
                    "Closing Cash (Exp/Act)": f"${exp['cash']} / ${entry['closing_cash']}",
                    "Ending Stock (Exp/Act)": f"{exp['stock']} / {entry['ending_stock']}",
                    "Status": "PASS" if row_pass else "FAIL",
                }
            )
        st.dataframe(pd.DataFrame(results_table), use_container_width=True, hide_index=True)
        if all_passed:
            st.success("✅ All 3 ROB fixture months and Balance Sheet reconciliations PASSED.")
        else:
            st.error("❌ One or more fixture checks FAILED.")