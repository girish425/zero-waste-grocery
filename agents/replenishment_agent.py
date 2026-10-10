"""
Replenishment & Procurement Agent
Specialized agent for reorder point monitoring, supplier lead times, and stockout prevention.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
import math
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy, ReplenishmentPolicy

class ReplenishmentAgent(BaseGroceryAgent):
    """
    Replenishment Agent:
    Identifies restocking needs based on stock, estimated demand, safety stock runway,
    and supplier lead times, while strictly suppressing reorders during impending spoilage.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-REPLEN-03",
            name="Replenishment & Procurement Agent",
            role="Safety Stock, Lead-Time & Restock Optimization",
            color_hex="#4338CA"
        )
        self.policy = policy or AgentWorkflowPolicy()

    def evaluate(
        self,
        batch_data: Dict[str, Any],
        demand_output: Optional[Dict[str, Any]] = None,
        freshness_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determines replenishment candidacy based on current stock, velocity, and lead time.
        """
        thoughts = []
        assumptions = []
        stock = float(batch_data.get("current_stock", 0))
        base_vel = batch_data.get("avg_daily_sales")
        unit_cost = float(batch_data.get("unit_cost", 2.0))
        
        replen_policy: ReplenishmentPolicy = getattr(self.policy, "replenishment", ReplenishmentPolicy())
        lead_time = int(batch_data.get("lead_time_days", replen_policy.default_lead_time_days))
        if "lead_time_days" not in batch_data:
            assumptions.append(f"Supplier delivery lead time was unrecorded; assumed default policy of {lead_time} days.")

        # 1. Missing Velocity Check: Prevent Unsupported Recommendations
        if base_vel is None or pd.isna(base_vel) or (hasattr(base_vel, "__len__") and len(base_vel) == 0):
            reason = "Sales velocity unrecorded in source data. Restock recommendations require historical sales velocity."
            assumptions.append("Sales velocity missing; procurement recommendation suppressed to prevent blind inventory ordering.")
            thoughts.append(self.log_thought("VELOCITY_UNRECORDED", "Sales velocity unrecorded for this SKU. Procurement held."))
            
            proposal = {
                "action": "HOLD_REORDER",
                "recommended_order_qty": 0,
                "urgency": "LOW",
                "confidence": 0.5,
                "reasoning": reason
            }
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="HOLD_REORDER",
                action_title="Hold Reorder (Sales Velocity Unrecorded)",
                supporting_evidence={"current_stock": stock, "sales_velocity": None},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.5
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "reorder_point": 0.0,
                "safety_stock": 0.0,
                "proposal": proposal,
                "recommendation": rec,
                "missing_information_or_assumptions": assumptions,
                "thoughts": thoughts
            }

        daily_rate = float(base_vel)
        if daily_rate <= 0:
            daily_rate = 0.1

        # 2. Extract Freshness Context
        risk_level = "LOW"
        surplus = 0.0
        if freshness_output and "risk_metrics" in freshness_output:
            risk_level = freshness_output["risk_metrics"].get("risk_level", "LOW")
            surplus = float(freshness_output["risk_metrics"].get("expected_surplus_units", 0.0))

        # 3. Calculate Safety Stock & Reorder Point
        z_factor = replen_policy.target_service_level_z
        lead_time_demand = daily_rate * lead_time
        safety_stock = round(z_factor * math.sqrt(max(0.1, lead_time_demand)) * 1.2, 0)
        reorder_point = lead_time_demand + safety_stock

        thoughts.append(self.log_thought(
            "CALCULATE_REORDER_POINT",
            f"Supplier lead time: {lead_time} days. Lead-time demand: {round(lead_time_demand, 1)} units. "
            f"Safety stock: {safety_stock} units. Reorder point: {round(reorder_point, 1)} units."
        ))

        # 4. Arbitration Rules: Spoilage Conflict Suppression
        if replen_policy.suppress_on_critical_spoilage and risk_level in ["CRITICAL", "HIGH"] and surplus > 2:
            reason = f"Surplus of {surplus:.1f} units pending near-term expiry spoilage risk. Restocking now would induce severe downstream waste."
            proposal = {
                "action": "HOLD_REORDER",
                "recommended_order_qty": 0,
                "urgency": "LOW",
                "confidence": 0.94,
                "reasoning": reason
            }
            thoughts.append(self.log_thought(
                "HOLD_ACTION",
                "Flagged critical spoilage risk on current batch. Reorder suppressed to prevent inventory bulking."
            ))
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="HOLD_REORDER",
                action_title="Suppress Reorder (Expiring Surplus Present)",
                supporting_evidence={
                    "current_stock": stock,
                    "reorder_point": round(reorder_point, 1),
                    "surplus_units": surplus,
                    "risk_level": risk_level
                },
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.94
            )
        elif stock <= reorder_point:
            # Need to reorder: Target configured days of coverage
            target_order_qty = int(max(
                replen_policy.min_order_qty,
                round(daily_rate * replen_policy.target_days_cover - stock + safety_stock)
            ))
            urgency = "HIGH" if stock <= safety_stock else "MEDIUM"
            reason = (
                f"Current stock ({stock:.0f} units) is at or below reorder threshold ({reorder_point:.1f} units). "
                f"Issuing PO for {target_order_qty} units maintains {z_factor*100/1.65:.0f}% service level with {lead_time}d lead time."
            )
            proposal = {
                "action": "REORDER",
                "recommended_order_qty": target_order_qty,
                "urgency": urgency,
                "confidence": 0.88,
                "reasoning": reason
            }
            thoughts.append(self.log_thought(
                "PROPOSE_REORDER",
                f"Generated restock proposal for {target_order_qty} units with supplier lead time of {lead_time} days."
            ))
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="REORDER",
                action_title=f"Issue Purchase Order for {target_order_qty} units",
                supporting_evidence={
                    "current_stock": stock,
                    "reorder_point": round(reorder_point, 1),
                    "safety_stock": safety_stock,
                    "lead_time_days": lead_time,
                    "daily_velocity": round(daily_rate, 1),
                    "recommended_order_qty": target_order_qty,
                    "estimated_procurement_cost_usd": round(target_order_qty * unit_cost, 2)
                },
                priority=urgency,
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.88
            )
        else:
            days_cover = round(stock / max(0.1, daily_rate), 1)
            reason = f"Current stock ({stock:.0f} units) exceeds reorder point ({reorder_point:.1f} units). Stock runway is healthy ({days_cover} days coverage)."
            proposal = {
                "action": "SUFFICIENT_STOCK",
                "recommended_order_qty": 0,
                "urgency": "LOW",
                "confidence": 0.90,
                "reasoning": reason
            }
            thoughts.append(self.log_thought(
                "SUFFICIENT_STOCK",
                f"Inventory runway is healthy ({days_cover} days coverage)."
            ))
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="SUFFICIENT_STOCK",
                action_title="Stock Level Adequate (No PO Needed)",
                supporting_evidence={
                    "current_stock": stock,
                    "reorder_point": round(reorder_point, 1),
                    "days_cover": days_cover
                },
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.90
            )

        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "reorder_point": round(reorder_point, 1),
            "safety_stock": safety_stock,
            "proposal": proposal,
            "recommendation": rec,
            "missing_information_or_assumptions": assumptions,
            "thoughts": thoughts
        }
