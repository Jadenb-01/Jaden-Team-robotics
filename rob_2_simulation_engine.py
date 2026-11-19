import json
import math
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

CENT = Decimal("0.01")


def D(val: Any) -> Decimal:
    """Quantize any numeric/string value to exact two-decimal USD cents."""
    if isinstance(val, Decimal):
        return val.quantize(CENT, rounding=ROUND_HALF_UP)
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)


def create_initial_state(
    team_id: str = "ROB-TEAM-01",
    selected_level: str = "Advanced",
    advanced_extension: str = "Seasonal Trigonometric",
    random_seed: int = 2027,
) -> Dict[str, Any]:
    """Initialize post-startup ROB-2 state per Career Venture Lab Student Handbook."""
    return {
        "team_id": team_id,
        "course": "Precalculus",
        "pathway_id": "ROB-2",
        "business_name": "Robotics Kit and Repair Studio",
        "snapshot_id": "SNAP-000",
        "state_version": 1,
        "simulation_date": "2027-01-01",
        "base_period": "monthly",
        "working_days": 22,
        "calendar_days": 30,
        "currency": "USD",
        "random_seed": int(random_seed),
        "selected_level": selected_level,
        "advanced_extension": advanced_extension,
        "level_approved_by_teacher": True,
        "level_by_skill": {
            "rational_average_cost": selected_level,
            "function_composition": selected_level,
            "seasonal_or_growth_modeling": selected_level,
        },
        "assumptions": [
            "All values are fictional teaching defaults from Career Venture Lab Handbook (ROB-2).",
            "Simplified accrual accounting: immediate customer cash payment; sales tax disabled.",
            "Depreciation is disabled at baseline (gross equipment = $4,000.00).",
            "Components are expensed when consumed in assembly; cash outflow occurs upon restock.",
            "Failed kits consume full variable costs (components + noncomponent) but yield $0 revenue.",
        ],
        "sources": [
            "Career Venture Lab Student Handbook (Nov 2026), Pages 24, 26, 69, 78-82."
        ],
        "offerings": [
            {
                "offering_id": "OFF-ROB-KIT",
                "name": "Introductory robot kit",
                "unit": "kit",
                "price": "120.00",
                "demand_rule": "q(p) = max(0, 80 - (1/3)p)",
                "capacity_rule": "floor(staff_hours / hours_per_unit)",
                "primary": True,
            },
            {
                "offering_id": "OFF-ROB-SEN",
                "name": "Sensor upgrade (Stage 2+ separate allocation)",
                "unit": "upgrade",
                "price": "45.00",
                "demand_rule": "separate allocation required",
                "capacity_rule": "separate allocation required",
                "primary": False,
            },
            {
                "offering_id": "OFF-ROB-REP",
                "name": "Repair service (Stage 2+ separate allocation)",
                "unit": "repair",
                "price": "60.00",
                "demand_rule": "separate allocation required",
                "capacity_rule": "separate allocation required",
                "primary": False,
            },
        ],
        "parameters": {
            "base_price": "120.00",
            "D0": 40,
            "staff_hours": 90.0,
            "hours_per_unit": 3.0,
            "component_unit_cost": "30.00",
            "defect_rate": 0.0,
        },
        "variable_cost_lines": {
            "components_COGS": "30.00",
            "assembly_labor": "20.00",
            "packaging": "10.00",
            "warranty_consumables": "5.00",
        },
        "fixed_cost_lines": {
            "workspace": "250.00",
            "software": "100.00",
            "equipment_maintenance": "150.00",
            "admin": "100.00",
        },
        "funding": [
            {
                "funding_id": "FUND-001",
                "date": "2027-01-01",
                "type": "owner_contribution",
                "amount": "12000.00",
                "terms": "Initial owner equity ($4,000 equipment, $3,000 inventory, $5,000 cash)",
            }
        ],
        "balances": {
            "cash": "5000.00",
            "inventory_units": 100,
            "inventory_value": "3000.00",
            "equipment_gross": "4000.00",
            "accumulated_depreciation": "0.00",
            "debt_principal": "0.00",
            "owner_contribution": "12000.00",
            "retained_earnings": "0.00",
        },
        "capacity": {
            "staff_hours": 90.0,
            "hours_per_unit": 3.0,
            "derived_capacity": 30,
        },
        "ledger": [],
        "campaigns": [],
        "decisions": [],
        "processed_run_ids": [],
        "processed_campaign_ids": [],
    }


def compute_unit_costs(state: Dict[str, Any]) -> Tuple[Decimal, Decimal, Decimal]:
    """Return (component_cost_per_unit, noncomponent_var_per_unit, total_var_per_unit)."""
    vc = state["variable_cost_lines"]
    comp = D(vc["components_COGS"])
    non_comp = D(vc["assembly_labor"]) + D(vc["packaging"]) + D(vc["warranty_consumables"])
    return comp, non_comp, comp + non_comp


def compute_fixed_cost(state: Dict[str, Any]) -> Decimal:
    """Return sum of monthly fixed expense lines."""
    return sum((D(v) for v in state["fixed_cost_lines"].values()), D("0.00"))


def compute_derived_capacity(state: Dict[str, Any]) -> int:
    """Derive monthly kit capacity from productive staff hours and hours per kit."""
    p = state["parameters"]
    if float(p["hours_per_unit"]) <= 0:
        return 0
    return math.floor(float(p["staff_hours"]) / float(p["hours_per_unit"]))


def check_balance_sheet(state: Dict[str, Any]) -> Dict[str, Any]:
    """Reconcile Assets = Liabilities + Equity."""
    b = state["balances"]
    cash = D(b["cash"])
    inv = D(b["inventory_value"])
    equip_net = D(b["equipment_gross"]) - D(b["accumulated_depreciation"])
    total_assets = cash + inv + equip_net

    debt = D(b["debt_principal"])
    equity = D(b["owner_contribution"]) + D(b["retained_earnings"])
    total_liab_equity = debt + equity
    diff = total_assets - total_liab_equity
    return {
        "cash": cash,
        "inventory_value": inv,
        "equipment_net": equip_net,
        "total_assets": total_assets,
        "debt_principal": debt,
        "owner_contribution": D(b["owner_contribution"]),
        "retained_earnings": D(b["retained_earnings"]),
        "total_equity": equity,
        "total_liab_equity": total_liab_equity,
        "difference": diff,
        "reconciled": abs(diff) <= D("0.01"),
    }


def run_monthly_step(
    state: Dict[str, Any],
    run_id: str,
    sim_date: str,
    requested: int,
    unit_price: Optional[Decimal] = None,
    restock_units: int = 0,
    ad_cost: Decimal = D("0.00"),
    campaign_id: Optional[str] = None,
    refund_amount: Decimal = D("0.00"),
    new_owner_cash: Decimal = D("0.00"),
    loan_cash: Decimal = D("0.00"),
    principal_repayment: Decimal = D("0.00"),
    interest_expense: Decimal = D("0.00"),
    additional_capex: Decimal = D("0.00"),
    capacity_override: Optional[int] = None,
    student_prediction: str = "",
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Execute one deterministic monthly simulation step for ROB-2.
    Enforces duplicate run_id protection, Robotics inventory timing, and defect rules.
    """
    if not run_id or not run_id.strip():
        return False, "Rejected: run_id is required.", state
    if run_id in state["processed_run_ids"]:
        return False, f"Rejected: Duplicate run_id '{run_id}'. No transaction created.", state
    if requested < 0 or restock_units < 0:
        return False, "Rejected: requested and restock_units must be nonnegative integers.", state

    money_inputs = [
        ad_cost,
        refund_amount,
        new_owner_cash,
        loan_cash,
        principal_repayment,
        interest_expense,
        additional_capex,
    ]
    if any(D(x) < D("0.00") for x in money_inputs):
        return False, "Rejected: monetary inputs cannot be negative.", state

    if campaign_id and D(ad_cost) > D("0.00"):
        if campaign_id in state["processed_campaign_ids"]:
            return False, f"Rejected: Duplicate campaign_id '{campaign_id}'. Campaign already charged.", state

    new_state = deepcopy(state)
    params = new_state["parameters"]
    price = D(unit_price) if unit_price is not None else D(params["base_price"])
    if price < D("0.00"):
        return False, "Rejected: unit_price cannot be negative.", state

    defect_rate = float(params["defect_rate"])
    if not (0.0 <= defect_rate <= 1.0):
        return False, "Rejected: defect_rate must be between 0 and 1.", state

    b = new_state["balances"]
    opening_cash = D(b["cash"])
    opening_stock = int(b["inventory_units"])
    opening_inv_val = D(b["inventory_value"])
    opening_debt = D(b["debt_principal"])

    if D(principal_repayment) > opening_debt + D(loan_cash):
        return False, "Rejected: principal repayment exceeds outstanding debt.", state

    comp_unit_cost, noncomp_unit_cost, _ = compute_unit_costs(new_state)
    fixed_cost = compute_fixed_cost(new_state)

    if capacity_override is not None:
        if capacity_override < 0:
            return False, "Rejected: capacity_override cannot be negative.", state
        capacity = int(capacity_override)
        mode_label = "FIXTURE_OVERRIDE"
    else:
        capacity = compute_derived_capacity(new_state)
        mode_label = "NORMAL_DERIVED"

    available_stock = opening_stock + int(restock_units)
    attempted = min(int(requested), capacity, available_stock)
    failed = math.floor(attempted * defect_rate)
    sold = attempted - failed
    lost_demand = max(0, int(requested) - attempted)

    # Robotics inventory rule: expensed when consumed; cash outflow occurs upon restock
    restock_cash_outflow = D(restock_units) * comp_unit_cost
    consumed_component_expense = D(attempted) * comp_unit_cost
    ending_stock = available_stock - attempted
    ending_inv_val = opening_inv_val + restock_cash_outflow - consumed_component_expense

    gross_revenue = price * D(sold)
    net_revenue = gross_revenue - D(refund_amount)
    noncomp_var_expense = D(attempted) * noncomp_unit_cost
    total_variable_expense = consumed_component_expense + noncomp_var_expense
    marketing_expense = D(ad_cost)
    total_operating_expense = total_variable_expense + fixed_cost + marketing_expense
    operating_profit = net_revenue - total_operating_expense
    net_profit = operating_profit - D(interest_expense)

    operating_cash_in = net_revenue
    operating_cash_out = (
        noncomp_var_expense
        + fixed_cost
        + marketing_expense
        + restock_cash_outflow
        + D(interest_expense)
    )
    investing_cash_out = D(additional_capex)
    financing_cash_net = D(new_owner_cash) + D(loan_cash) - D(principal_repayment)
    closing_cash = opening_cash + operating_cash_in - operating_cash_out - investing_cash_out + financing_cash_net

    if closing_cash < D("0.00"):
        return False, f"Rejected: Insufficient cash (closing cash would be ${closing_cash}).", state

    b["cash"] = str(closing_cash)
    b["inventory_units"] = ending_stock
    b["inventory_value"] = str(ending_inv_val)
    b["equipment_gross"] = str(D(b["equipment_gross"]) + D(additional_capex))
    b["debt_principal"] = str(opening_debt + D(loan_cash) - D(principal_repayment))
    b["owner_contribution"] = str(D(b["owner_contribution"]) + D(new_owner_cash))
    b["retained_earnings"] = str(D(b["retained_earnings"]) + net_profit)

    new_version = int(new_state["state_version"]) + 1
    new_state["state_version"] = new_version
    new_state["snapshot_id"] = f"SNAP-{new_version:03d}"
    new_state["simulation_date"] = sim_date
    new_state["capacity"]["staff_hours"] = float(params["staff_hours"])
    new_state["capacity"]["hours_per_unit"] = float(params["hours_per_unit"])
    new_state["capacity"]["derived_capacity"] = capacity
    new_state["processed_run_ids"].append(run_id)
    if campaign_id and marketing_expense > D("0.00"):
        new_state["processed_campaign_ids"].append(campaign_id)

    record = {
        "transaction_id": f"TXN-{new_version:03d}-{run_id}",
        "run_id": run_id,
        "date": sim_date,
        "mode": mode_label,
        "state_version": new_version,
        "requested": int(requested),
        "capacity": capacity,
        "attempted": attempted,
        "failed": failed,
        "sold": sold,
        "lost_demand": lost_demand,
        "unit_price": str(price),
        "gross_revenue": str(gross_revenue),
        "refund_amount": str(D(refund_amount)),
        "net_revenue": str(net_revenue),
        "consumed_component_expense": str(consumed_component_expense),
        "noncomp_var_expense": str(noncomp_var_expense),
        "total_variable_expense": str(total_variable_expense),
        "fixed_expense": str(fixed_cost),
        "marketing_expense": str(marketing_expense),
        "campaign_id": campaign_id or "",
        "total_operating_expense": str(total_operating_expense),
        "operating_profit": str(operating_profit),
        "interest_expense": str(D(interest_expense)),
        "net_profit": str(net_profit),
        "restock_units": int(restock_units),
        "restock_cash_outflow": str(restock_cash_outflow),
        "additional_capex": str(D(additional_capex)),
        "new_owner_cash": str(D(new_owner_cash)),
        "loan_cash": str(D(loan_cash)),
        "principal_repayment": str(D(principal_repayment)),
        "opening_cash": str(opening_cash),
        "closing_cash": str(closing_cash),
        "opening_stock": opening_stock,
        "ending_stock": ending_stock,
        "ending_inventory_value": str(ending_inv_val),
        "student_prediction": student_prediction,
    }
    new_state["ledger"].append(record)
    return True, f"Recorded '{run_id}' (state_version v{new_version}).", new_state


def validate_and_import_snapshot(
    raw_json: str, expected_team_id: str, current_version: int
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Validate team_id, pathway_id, state_version freshness, and balance reconciliation."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return False, f"Rejected import: invalid JSON ({exc}).", None

    required_keys = [
        "team_id",
        "course",
        "pathway_id",
        "snapshot_id",
        "state_version",
        "parameters",
        "variable_cost_lines",
        "fixed_cost_lines",
        "balances",
        "ledger",
    ]
    missing = [k for k in required_keys if k not in data]
    if missing:
        return False, f"Rejected import: missing required fields {missing}.", None

    if data["team_id"] != expected_team_id:
        return (
            False,
            f"Rejected import: team_id '{data['team_id']}' does not match '{expected_team_id}'.",
            None,
        )

    if data.get("pathway_id") != "ROB-2":
        return (
            False,
            f"Rejected import: pathway_id '{data.get('pathway_id')}' does not match 'ROB-2'.",
            None,
        )

    if int(data["state_version"]) < int(current_version):
        return (
            False,
            f"Rejected stale record: imported v{data['state_version']} is older than current v{current_version}.",
            None,
        )

    bal = check_balance_sheet(data)
    if not bal["reconciled"]:
        return (
            False,
            f"Rejected import: Assets (${bal['total_assets']}) != Liabilities + Equity (${bal['total_liab_equity']}).",
            None,
        )

    return True, f"Restored {data['snapshot_id']} (state_version v{data['state_version']}).", data


def aggregate_ledger_horizon(ledger: List[Dict[str, Any]], horizon: str, working_days: int = 22) -> List[Dict[str, Any]]:
    """Aggregate dated event ledger into Monthly (observed), Yearly, or Daily (modeled allocation)."""
    if not ledger:
        return []

    if horizon == "Monthly (Observed Ledger)":
        return [
            {
                "period": row["date"][:7],
                "label": "ACTUAL LEDGER (MONTHLY)",
                "requested": row["requested"],
                "sold": row["sold"],
                "net_revenue": float(D(row["net_revenue"])),
                "total_expense": float(D(row["total_operating_expense"])),
                "operating_profit": float(D(row["operating_profit"])),
                "closing_cash": float(D(row["closing_cash"])),
                "ending_stock": row["ending_stock"],
            }
            for row in ledger
        ]

    if horizon == "Yearly (Aggregated Ledger)":
        yearly: Dict[str, Dict[str, Any]] = {}
        for row in ledger:
            yr = row["date"][:4]
            if yr not in yearly:
                yearly[yr] = {
                    "period": yr,
                    "label": "ACTUAL LEDGER (YEARLY SUM)",
                    "requested": 0,
                    "sold": 0,
                    "net_revenue": 0.0,
                    "total_expense": 0.0,
                    "operating_profit": 0.0,
                    "closing_cash": 0.0,
                    "ending_stock": 0,
                }
            yearly[yr]["requested"] += int(row["requested"])
            yearly[yr]["sold"] += int(row["sold"])
            yearly[yr]["net_revenue"] = round(yearly[yr]["net_revenue"] + float(D(row["net_revenue"])), 2)
            yearly[yr]["total_expense"] = round(yearly[yr]["total_expense"] + float(D(row["total_operating_expense"])), 2)
            yearly[yr]["operating_profit"] = round(yearly[yr]["operating_profit"] + float(D(row["operating_profit"])), 2)
            yearly[yr]["closing_cash"] = float(D(row["closing_cash"]))
            yearly[yr]["ending_stock"] = int(row["ending_stock"])
        return list(yearly.values())

    # Daily (Modeled Allocation using working_days, never multiplying monthly by 30)
    wd = max(1, int(working_days))
    return [
        {
            "period": f"{row['date'][:7]} (per working day, n={wd})",
            "label": "MODELED DAILY ALLOCATION (NOT OBSERVED DAILY SALES)",
            "requested": round(int(row["requested"]) / wd, 2),
            "sold": round(int(row["sold"]) / wd, 2),
            "net_revenue": round(float(D(row["net_revenue"])) / wd, 2),
            "total_expense": round(float(D(row["total_operating_expense"])) / wd, 2),
            "operating_profit": round(float(D(row["operating_profit"])) / wd, 2),
            "closing_cash": float(D(row["closing_cash"])),
            "ending_stock": row["ending_stock"],
        }
        for row in ledger
    ]


# --- Precalculus ROB-2 Functions ---

def precalc_average_cost(s: float, fixed_cost: float = 600.0, var_cost: float = 65.0) -> Optional[float]:
    """Foundation: A(s) = F/s + v for 0 < s <= capacity; undefined at s = 0."""
    if s <= 0:
        return None
    return fixed_cost / s + var_cost


def precalc_composed_demand(p: float, D0: float = 40.0, p0: float = 120.0) -> float:
    """Applied: q(p) = max(0, 2*D0 - (D0/p0)*p) on 0 <= p <= 2*p0."""
    return max(0.0, 2.0 * D0 - (D0 / p0) * p)


def precalc_composed_profit(
    p: float,
    D0: float = 40.0,
    p0: float = 120.0,
    capacity: int = 30,
    F: float = 600.0,
    v: float = 65.0,
) -> Dict[str, float]:
    """Applied: Compose q(p), s(p)=min(cap, q(p)), R(p), C(s(p)), and P(p)."""
    q_cont = precalc_composed_demand(p, D0, p0)
    s_cont = min(float(capacity), q_cont)
    s_int = min(int(capacity), math.floor(q_cont))

    rev_cont = p * s_cont
    cost_cont = F + v * s_cont
    prof_cont = rev_cont - cost_cont

    rev_int = p * s_int
    cost_int = F + v * s_int
    prof_int = rev_int - cost_int

    breakpoint_p = p0 * (2.0 - float(capacity) / D0) if D0 > 0 else 0.0
    return {
        "price_p": p,
        "demand_q_cont": q_cont,
        "sales_s_cont": s_cont,
        "sales_s_int": float(s_int),
        "revenue_cont": rev_cont,
        "cost_cont": cost_cont,
        "profit_cont": prof_cont,
        "profit_int": prof_int,
        "breakpoint_p": breakpoint_p,
    }


def precalc_seasonal_demand(t: int, D0: float = 40.0, capacity: int = 30) -> Dict[str, float]:
    """Advanced Option A: D(t) = D0 * (1 + 0.20 * sin(2*pi*(t-1)/12)), peak t=4, trough t=10."""
    d_raw = D0 * (1.0 + 0.20 * math.sin(2.0 * math.pi * (t - 1) / 12.0))
    s_cont = min(float(capacity), d_raw)
    s_int = min(int(capacity), math.floor(d_raw))
    return {
        "month_t": t,
        "demand_raw": d_raw,
        "sales_clipped_cont": s_cont,
        "sales_clipped_int": float(s_int),
        "unserved_cont": max(0.0, d_raw - s_cont),
    }


def precalc_growth_target(
    t: int, D0: float = 40.0, monthly_growth_rate: float = 0.05, target_demand: float = 60.0, capacity: int = 30
) -> Dict[str, float]:
    """Advanced Option B: D(t) = D0 * (1 + r)^(t-1) and logarithmic months-to-target solver."""
    d_raw = D0 * ((1.0 + monthly_growth_rate) ** (t - 1))
    s_cont = min(float(capacity), d_raw)
    s_int = min(int(capacity), math.floor(d_raw))
    if monthly_growth_rate > 0 and target_demand > D0 and D0 > 0:
        months_to_target = 1.0 + math.log(target_demand / D0) / math.log(1.0 + monthly_growth_rate)
    else:
        months_to_target = 1.0
    return {
        "month_t": t,
        "demand_raw": d_raw,
        "sales_clipped_cont": s_cont,
        "sales_clipped_int": float(s_int),
        "months_to_target": months_to_target,
    }