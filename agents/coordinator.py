"""
Chief Coordinator Agent
Arbitrates agent proposals, resolves trade-offs, enforces business rules,
and produces EXACTLY ONE reconciled action per SKU & store for planner approval.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy
from agents.demand_agent import DemandAgent
from agents.freshness_agent import FreshnessAgent
from agents.replenishment_agent import ReplenishmentAgent
from agents.discount_agent import DiscountAgent
from agents.transfer_agent import StoreTransferAgent
from agents.llm_explainer import explain_recommendation_in_plain_language

class CoordinatorAgent(BaseGroceryAgent):
    """
    Chief Coordinator Agent:
    Orchestrates the multi-agent consensus workflow, combines individual agent votes,
    resolves operational trade-offs, eliminates duplicate/conflicting proposals,
    assigns priorities, and produces a unified action list for human review.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-COORD-00",
            name="Chief Coordinator Agent",
            role="Multi-Agent Consensus Arbitration & Action Optimization",
            color_hex="#059669"
        )
        self.policy = policy or AgentWorkflowPolicy()
        self.demand_agent = DemandAgent(policy=self.policy)
        self.freshness_agent = FreshnessAgent(policy=self.policy)
        self.replen_agent = ReplenishmentAgent(policy=self.policy)
        self.discount_agent = DiscountAgent(policy=self.policy)
        self.transfer_agent = StoreTransferAgent(policy=self.policy)

    def reconcile_batch(
        self,
        batch_data: Dict[str, Any],
        all_inventory_df: Optional[pd.DataFrame] = None,
        temp_delta_c: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes multi-agent consensus workflow for a single batch and returns
        exactly one reconciled action with transparent explainability.
        """
        trace = []
        all_assumptions = []

        sku = str(batch_data.get("sku", "UNKNOWN_SKU"))
        product_name = str(batch_data.get("product_name", "Unknown Product"))
        store_id = str(batch_data.get("store_id", "STORE-01"))
        store_name = str(batch_data.get("store_name", "Primary Store"))
        raw_dte = batch_data.get("days_to_expiry")
        stock = float(batch_data.get("current_stock", 0))
        unit_cost = float(batch_data.get("unit_cost", 2.0))
        base_price = float(batch_data.get("base_price", 3.5))
        carbon_factor = float(batch_data.get("carbon_factor_kg", 1.8))
        
        dte_disp = f"{raw_dte}d" if (raw_dte is not None and not pd.isna(raw_dte)) else "Unspecified"
        trace.append(self.log_thought(
            "DISPATCH_SPECIALISTS",
            f"Coordinator evaluating SKU {sku} ({product_name}) at {store_name}. Stock: {stock} units, Days to expiry: {dte_disp}."
        ))
        
        # 1. Run Demand Agent
        demand_res = self.demand_agent.evaluate(batch_data, temp_delta_c=temp_delta_c)
        trace.extend(demand_res["thoughts"])
        all_assumptions.extend(demand_res.get("missing_information_or_assumptions", []))
        
        # 2. Run Freshness & Spoilage Agent
        freshness_res = self.freshness_agent.evaluate(batch_data, demand_res)
        trace.extend(freshness_res["thoughts"])
        all_assumptions.extend(freshness_res.get("missing_information_or_assumptions", []))
        
        # 3. Run Replenishment Agent
        replen_res = self.replen_agent.evaluate(batch_data, demand_res, freshness_res)
        trace.extend(replen_res["thoughts"])
        all_assumptions.extend(replen_res.get("missing_information_or_assumptions", []))
        
        # 4. Run Discount Agent
        discount_res = self.discount_agent.evaluate(batch_data, demand_res, freshness_res)
        trace.extend(discount_res["thoughts"])
        all_assumptions.extend(discount_res.get("missing_information_or_assumptions", []))
        
        # 5. Run Inter-Store Transfer Agent
        transfer_res = self.transfer_agent.evaluate(batch_data, all_inventory_df, freshness_res)
        trace.extend(transfer_res["thoughts"])
        all_assumptions.extend(transfer_res.get("missing_information_or_assumptions", []))
        
        # Deduplicate assumptions
        unique_assumptions = list(dict.fromkeys(all_assumptions))

        # 6. Arbitration & Conflict Resolution Logic
        surplus = freshness_res["risk_metrics"]["expected_surplus_units"]
        has_expiry = raw_dte is not None and not pd.isna(raw_dte)
        dte = int(raw_dte) if has_expiry else None

        final_action = "MAINTAIN"
        action_title = "Optimal Shelf Velocity (No Intervention Needed)"
        action_details = {}
        priority = "LOW"
        urgency = "LOW"
        margin_impact = 0.0
        waste_saved_units = 0.0
        generating_specialist = self.name
        explanation = ""

        # CONFLICT RESOLUTION RULE 1: Unspecified Expiry
        if dte is None:
            final_action = "MAINTAIN"
            action_title = "Standard Monitoring (Expiry Date Unspecified)"
            action_details = {
                "status": "Unspecified Expiry",
                "note": "Expiry date was not provided in dataset. Biological hazard cannot be assumed."
            }
            priority = "LOW"
            urgency = "UNKNOWN"
            margin_impact = 0.0
            waste_saved_units = 0.0
            generating_specialist = self.freshness_agent.name
            explanation = "Product has unrecorded expiry date. Standard retail velocity maintained without speculative discounting or disposal."

        # CONFLICT RESOLUTION RULE 2: Already Expired or Due Today (DTE <= 0)
        elif dte <= 0:
            generating_specialist = self.freshness_agent.name
            priority = "CRITICAL"
            if stock > 8:
                final_action = "DONATE"
                action_title = f"Dispatch {int(stock)} units to Community Food Bank"
                action_details = {
                    "donation_partner": "City Harvest / Feeding America Partner",
                    "tax_deduction_usd": round(stock * unit_cost, 2),
                    "units": stock
                }
                margin_impact = round(stock * unit_cost * 0.5, 2) # Tax credit proxy
                waste_saved_units = stock
                explanation = f"Product has reached expiry date. Donating {int(stock)} units preserves nutritional value and earns tax salvage (${margin_impact:.2f})."
            else:
                final_action = "MARKDOWN"
                action_title = f"Flash Clearance 60% Off (${round(base_price * 0.4, 2)})"
                action_details = discount_res["proposal"]
                margin_impact = discount_res["proposal"].get("recovered_margin_usd", 0.0)
                waste_saved_units = stock
                generating_specialist = self.discount_agent.name
                explanation = f"Product at final shelf day. 60% flash clearance markdown applied to clear remaining {int(stock)} units."

        # CONFLICT RESOLUTION RULE 3: Critical Expiry in 24h (DTE == 1) with Surplus
        elif dte == 1 and surplus > 1:
            final_action = "MARKDOWN"
            disc = discount_res["proposal"].get("discount_pct", 30)
            new_p = discount_res["proposal"].get("discounted_price", round(base_price * 0.7, 2))
            action_title = f"Apply {disc}% Dynamic Markdown (${new_p})"
            action_details = discount_res["proposal"]
            priority = "CRITICAL"
            margin_impact = discount_res["proposal"].get("recovered_margin_usd", 0.0)
            waste_saved_units = surplus
            generating_specialist = self.discount_agent.name
            explanation = f"Product expires in 24 hours with {surplus:.1f}u surplus. Implemented {disc}% dynamic markdown to accelerate sell-through."

        # CONFLICT RESOLUTION RULE 4: Multi-Store Transfer takes precedence over markdown if DTE >= 2 & Net Salvage Positive
        elif dte >= 2 and transfer_res["proposal"].get("action") == "INTER_STORE_TRANSFER":
            final_action = "TRANSFER"
            t_qty = transfer_res["proposal"]["transfer_qty"]
            dest_name = transfer_res["proposal"]["destination_store_name"]
            action_title = f"Transfer {t_qty} units to {dest_name}"
            action_details = transfer_res["proposal"]
            priority = "HIGH"
            margin_impact = transfer_res["proposal"].get("projected_salvage_usd", 0.0)
            waste_saved_units = t_qty
            generating_specialist = self.transfer_agent.name
            explanation = (
                f"Cross-store transfer of {t_qty} units to {dest_name} captures full retail price (${base_price:.2f}), "
                f"yielding higher net return (${margin_impact:.2f}) than a markdown discount."
            )

        # CONFLICT RESOLUTION RULE 5: Moderate Surplus with No Viable Transfer -> Preventive Markdown
        elif surplus > 2 and discount_res["proposal"].get("action") == "DYNAMIC_MARKDOWN":
            final_action = "MARKDOWN"
            disc = discount_res["proposal"].get("discount_pct", 20)
            new_p = discount_res["proposal"].get("discounted_price", round(base_price * 0.8, 2))
            action_title = f"Apply {disc}% Preventive Markdown (${new_p})"
            action_details = discount_res["proposal"]
            priority = "MEDIUM"
            margin_impact = discount_res["proposal"].get("recovered_margin_usd", 0.0)
            waste_saved_units = surplus
            generating_specialist = self.discount_agent.name
            explanation = f"Surplus of {surplus:.1f} units detected. Preventive {disc}% discount implemented to balance velocity before expiry."

        # CONFLICT RESOLUTION RULE 6: Inventory Runway Low with No Spoilage Conflict -> Replenish
        elif replen_res["proposal"].get("action") == "REORDER":
            final_action = "REORDER"
            order_qty = replen_res["proposal"]["recommended_order_qty"]
            action_title = f"Issue PO for {order_qty} units (Supplier Restock)"
            action_details = replen_res["proposal"]
            priority = replen_res["proposal"]["urgency"]
            margin_impact = -round(order_qty * unit_cost, 2)
            waste_saved_units = 0.0
            generating_specialist = self.replen_agent.name
            explanation = f"Stock level ({stock:.0f} units) breached safety reorder point. Initiated restock purchase order for {order_qty} units."

        # CONFLICT RESOLUTION RULE 7: Balanced Inventory -> Maintain
        else:
            final_action = "MAINTAIN"
            vel_val = batch_data.get("avg_daily_sales") or 10.0
            coverage_days = round(stock / max(0.1, float(vel_val)), 1)
            action_title = "Optimal Shelf Velocity (No Intervention Needed)"
            action_details = {"status": "Nominal", "days_coverage": coverage_days}
            priority = "LOW"
            margin_impact = 0.0
            waste_saved_units = 0.0
            generating_specialist = self.name
            explanation = f"Stock coverage ({coverage_days} days) matches consumer demand. No markdown, transfer, or reorder required."

        trace.append(self.log_thought(
            "ARBITRATION_COMPLETE",
            f"Coordinator selected [{final_action}]: {action_title}. Priority: {priority}. Specialist: {generating_specialist}."
        ))

        carbon_saved_kg = round(waste_saved_units * carbon_factor, 2)

        # Build Standardized Recommendation Object
        supporting_evidence = {
            "current_stock": stock,
            "days_to_expiry": dte,
            "expected_surplus_units": surplus,
            "margin_impact_usd": round(margin_impact, 2),
            "waste_saved_units": round(waste_saved_units, 1),
            "carbon_saved_kg": carbon_saved_kg,
            "spoilage_risk_tier": freshness_res["risk_metrics"]["risk_level"],
            "cumulative_demand_forecast": demand_res["cumulative_demand_p50"]
        }
        supporting_evidence.update(action_details)

        # Optional LLM natural language explanation synthesis
        if self.policy.llm_enabled:
            explanation = explain_recommendation_in_plain_language(
                recommendation={
                    "product": batch_data,
                    "proposed_action": final_action,
                    "supporting_evidence": supporting_evidence,
                    "missing_information_or_assumptions": unique_assumptions,
                    "priority": priority
                },
                api_key=self.policy.llm_api_key,
                model_name=self.policy.llm_model
            )

        recommendation = self.create_recommendation(
            product=batch_data,
            proposed_action=final_action,
            action_title=action_title,
            supporting_evidence=supporting_evidence,
            priority=priority,
            explanation=explanation,
            missing_information_or_assumptions=unique_assumptions,
            confidence=0.92,
            extra_details={
                "generating_specialist": generating_specialist,
                "arbitrated_by": self.name
            }
        )

        return {
            "batch_id": batch_data.get("batch_id", ""),
            "batch_code": batch_data.get("batch_code", ""),
            "store_id": store_id,
            "store_name": store_name,
            "sku": sku,
            "product_name": product_name,
            "category": batch_data.get("category", "General"),
            "current_stock": stock,
            "days_to_expiry": dte,
            "final_action": final_action,
            "action_title": action_title,
            "action_details": action_details,
            "urgency": urgency if dte is None else priority, # UI uses 'urgency'
            "priority": priority,
            "margin_impact_usd": round(margin_impact, 2),
            "waste_saved_units": round(waste_saved_units, 1),
            "carbon_saved_kg": carbon_saved_kg,
            "spoilage_prob": freshness_res["risk_metrics"]["spoilage_probability"],
            "financial_risk_usd": freshness_res["risk_metrics"]["financial_risk_usd"],
            "generating_agent": generating_specialist,
            "generating_specialist": generating_specialist,
            "agent_votes": {
                "Demand": f"{demand_res['cumulative_demand_p50']}u forecasted",
                "Freshness": f"{freshness_res['risk_metrics']['risk_level']} ({freshness_res['risk_metrics']['expected_spoiled_units']}u at risk)",
                "Spoilage": f"{freshness_res['risk_metrics']['risk_level']} ({freshness_res['risk_metrics']['expected_spoiled_units']}u at risk)",
                "Replenishment": replen_res["proposal"]["action"],
                "Discount": f"{discount_res['proposal'].get('discount_pct', 0)}% off" if discount_res["proposal"]["action"] != "NO_MARKDOWN" else "None",
                "Markdown": f"{discount_res['proposal'].get('discount_pct', 0)}% off" if discount_res["proposal"]["action"] != "NO_MARKDOWN" else "None",
                "Transfer": "Transfer candidate" if transfer_res["proposal"]["action"] == "INTER_STORE_TRANSFER" else "No transfer"
            },
            "recommendation": recommendation,
            "supporting_evidence": supporting_evidence,
            "missing_information_or_assumptions": unique_assumptions,
            "explanation": explanation,
            "reasoning_trace": trace,
            "approval_status": "PENDING"
        }

    def reconcile_all(
        self,
        all_inventory_df: pd.DataFrame,
        temp_delta_c: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Executes consensus deliberation across an entire inventory DataFrame.
        """
        if all_inventory_df is None or all_inventory_df.empty:
            return []

        proposals = []
        for _, row in all_inventory_df.iterrows():
            batch_dict = row.to_dict()
            prop = self.reconcile_batch(
                batch_data=batch_dict,
                all_inventory_df=all_inventory_df,
                temp_delta_c=temp_delta_c
            )
            proposals.append(prop)
        return proposals
