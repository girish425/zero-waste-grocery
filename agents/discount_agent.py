"""
Discount & Dynamic Markdown Agent
Specialized agent for elasticity-based price adjustments to accelerate inventory velocity before expiry.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy, DiscountPolicy

class DiscountAgent(BaseGroceryAgent):
    """
    Discount Agent:
    Suggests a defensible markdown for products at risk of expiry,
    strictly enforcing policy checks, elasticity limits, and data sufficiency.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-DISCOUNT-04",
            name="Discount & Dynamic Markdown Agent",
            role="Elasticity-Driven Discounting & Margin Recovery",
            color_hex="#C2410C"
        )
        self.policy = policy or AgentWorkflowPolicy()

    def evaluate(
        self,
        batch_data: Dict[str, Any],
        demand_output: Optional[Dict[str, Any]] = None,
        freshness_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculates optimal markdown tier to clear excess stock prior to expiry while maximizing net margin.
        Enforces policy availability and data sufficiency constraints.
        """
        thoughts = []
        assumptions = []
        stock = float(batch_data.get("current_stock", 0))
        base_price = float(batch_data.get("base_price", 0.0))
        unit_cost = float(batch_data.get("unit_cost", 0.0))
        raw_dte = batch_data.get("days_to_expiry")

        # 1. Policy Availability Check
        disc_policy: Optional[DiscountPolicy] = getattr(self.policy, "discount", None)
        if disc_policy is None or not getattr(disc_policy, "enabled", False):
            reason = "Discount calculation skipped: An explicit discount policy is disabled or unconfigured."
            thoughts.append(self.log_thought("POLICY_DISABLED", reason))
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_MARKDOWN",
                action_title="Maintain Full Price (Markdown Policy Inactive)",
                supporting_evidence={"policy_enabled": False, "base_price": base_price},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=["Explicit discount policy was disabled or absent in agent configuration."],
                confidence=1.0
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_MARKDOWN", "discount_pct": 0, "discounted_price": base_price, "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": ["Discount policy disabled"],
                "thoughts": thoughts
            }

        # 2. Data Sufficiency Check: Required Fields
        if base_price <= 0:
            reason = "Base retail price is missing or zero. Cannot calculate discount without pricing baseline."
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_MARKDOWN",
                action_title="Maintain Full Price (Missing Base Price)",
                supporting_evidence={"base_price": base_price},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=["Base retail price missing or non-positive."],
                confidence=0.5
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_MARKDOWN", "discount_pct": 0, "discounted_price": base_price, "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": ["Missing base price"],
                "thoughts": [self.log_thought("MISSING_PRICE", reason)]
            }

        # Expiry date integrity
        if raw_dte is None or pd.isna(raw_dte):
            reason = "Expiry date is unspecified in source data. Markdowns cannot be justified without verified expiry risk."
            assumptions.append("Product has unspecified expiry; promotional markdown withheld to protect retail margin.")
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_MARKDOWN",
                action_title="Maintain Regular Price (Expiry Unspecified)",
                supporting_evidence={"days_to_expiry": None, "base_price": base_price},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.85
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_MARKDOWN", "discount_pct": 0, "discounted_price": base_price, "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": assumptions,
                "thoughts": [self.log_thought("UNSPECIFIED_EXPIRY", reason)]
            }

        dte = int(raw_dte)
        cum_demand = float(demand_output.get("cumulative_demand_p50", max(1.0, stock * 0.5))) if demand_output else max(1.0, stock * 0.5)
        
        # Determine surplus units
        if freshness_output and "risk_metrics" in freshness_output:
            surplus = float(freshness_output["risk_metrics"].get("expected_surplus_units", max(0.0, stock - cum_demand)))
        else:
            surplus = max(0.0, stock - cum_demand)

        # 3. No Surplus Check
        if surplus <= disc_policy.min_surplus_units:
            reason = f"Inventory velocity is healthy. Expected demand ({cum_demand:.1f}u) absorbs stock ({stock:.0f}u) before expiry. Full price maintained."
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_MARKDOWN",
                action_title=f"Maintain Regular Price (${base_price:.2f})",
                supporting_evidence={"stock": stock, "demand": cum_demand, "surplus": surplus},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=[],
                confidence=0.92
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_MARKDOWN", "discount_pct": 0, "discounted_price": base_price, "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": [],
                "thoughts": [self.log_thought("NO_ACTION_REQUIRED", reason)]
            }

        # 4. Compute Elasticity Lift
        elasticity = disc_policy.price_elasticity
        thoughts.append(self.log_thought(
            "COMPUTE_ELASTICITY_LIFT",
            f"Detected surplus of {surplus:.1f} units across {dte} day(s). Baseline demand: {cum_demand:.1f}u. Price elasticity epsilon: {elasticity}."
        ))

        # Required lift factor: stock / demand
        required_lift = min(3.5, max(1.1, stock / max(0.5, cum_demand)))
        target_price_ratio = required_lift ** (1.0 / elasticity)
        raw_discount_pct = (1.0 - target_price_ratio) * 100.0

        # Discretize into retail markdown tiers from policy
        if dte <= 0:
            discount_tier = disc_policy.default_tiers.get(0, 60) # Final day clearance
        elif dte == 1:
            discount_tier = disc_policy.default_tiers.get(1, 40) if raw_discount_pct >= 30 else 30
        elif dte == 2:
            discount_tier = disc_policy.default_tiers.get(2, 25) if raw_discount_pct >= 20 else 15
        else:
            discount_tier = disc_policy.default_tiers.get(3, 15)

        # Cap by policy maximum
        discount_tier = min(disc_policy.max_discount_pct, discount_tier)
        discounted_price = round(base_price * (1.0 - discount_tier / 100.0), 2)

        # Financial impact
        boosted_demand = cum_demand * ((1.0 - discount_tier / 100.0) ** elasticity)
        cleared_units = min(stock, boosted_demand)
        recovered_revenue = round(cleared_units * discounted_price, 2)
        recovered_margin = round(cleared_units * (discounted_price - unit_cost), 2)

        priority = "CRITICAL" if dte <= 1 else ("HIGH" if dte == 2 else "MEDIUM")
        explanation = (
            f"Recommended {discount_tier}% dynamic markdown (New price: ${discounted_price:.2f} vs regular ${base_price:.2f}). "
            f"Based on price elasticity {elasticity}, expected clearance is {cleared_units:.1f} units, recovering ${recovered_margin:.2f} gross margin "
            f"and preventing {surplus:.1f} units from being wasted."
        )

        thoughts.append(self.log_thought(
            "OPTIMAL_TIER_SELECTED",
            f"Recommended {discount_tier}% markdown (New price: ${discounted_price} vs regular ${base_price}). "
            f"Expected clearance: {round(cleared_units, 1)} units. Net recovered margin: ${recovered_margin}."
        ))

        proposal_dict = {
            "action": "DYNAMIC_MARKDOWN",
            "discount_pct": discount_tier,
            "discounted_price": discounted_price,
            "original_price": base_price,
            "expected_cleared_units": round(cleared_units, 1),
            "recovered_margin_usd": recovered_margin,
            "recovered_revenue_usd": recovered_revenue,
            "urgency": priority,
            "confidence": 0.90,
            "reasoning": explanation
        }

        rec = self.create_recommendation(
            product=batch_data,
            proposed_action="MARKDOWN",
            action_title=f"Apply {discount_tier}% Dynamic Markdown (${discounted_price:.2f})",
            supporting_evidence={
                "current_stock": stock,
                "days_to_expiry": dte,
                "original_price": base_price,
                "discounted_price": discounted_price,
                "discount_pct": discount_tier,
                "surplus_units": surplus,
                "expected_cleared_units": round(cleared_units, 1),
                "recovered_margin_usd": recovered_margin,
                "elasticity": elasticity
            },
            priority=priority,
            explanation=explanation,
            missing_information_or_assumptions=assumptions,
            confidence=0.90
        )

        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "proposal": proposal_dict,
            "recommendation": rec,
            "missing_information_or_assumptions": assumptions,
            "thoughts": thoughts
        }

# Alias for backward compatibility
MarkdownPricingAgent = DiscountAgent
