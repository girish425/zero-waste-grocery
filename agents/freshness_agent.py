"""
Freshness & Spoilage Agent
Specialized agent for shelf-life monitoring, biological decay hazards, and waste carbon metrics.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy
from models.spoilage_risk import SpoilageRiskEvaluator

class FreshnessAgent(BaseGroceryAgent):
    """
    Freshness Agent:
    Identifies products nearing expiry or already expired, calculates remaining shelf-life,
    models Arrhenius temperature-accelerated decay, and evaluates biological spoilage risk.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-FRESH-02",
            name="Freshness & Spoilage Agent",
            role="Biological Shelf-Life & Waste Risk Quantification",
            color_hex="#EA580C"
        )
        self.policy = policy or AgentWorkflowPolicy()
        self.risk_evaluator = SpoilageRiskEvaluator()

    def evaluate(
        self,
        batch_data: Dict[str, Any],
        demand_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assesses biological degradation hazard and waste impact.
        """
        thoughts = []
        assumptions = []
        stock = float(batch_data.get("current_stock", 0))
        raw_dte = batch_data.get("days_to_expiry")
        cum_demand = float(demand_output.get("cumulative_demand_p50", max(1.0, stock * 0.5))) if demand_output else max(1.0, stock * 0.5)
        unit_cost = float(batch_data.get("unit_cost", 2.0))
        base_price = float(batch_data.get("base_price", 3.5))
        carbon_factor = float(batch_data.get("carbon_factor_kg", 1.8))
        actual_temp = float(batch_data.get("storage_temp_c", self.policy.freshness.default_storage_temp_c))
        target_temp = float(batch_data.get("target_temp_c", self.policy.freshness.default_storage_temp_c))

        if "storage_temp_c" not in batch_data:
            assumptions.append("Cold-chain storage temperature was unrecorded; assumed nominal target 4.0°C.")

        # Handle missing or unspecified expiry dates
        if raw_dte is None or pd.isna(raw_dte):
            assumptions.append("Expiry date is unspecified in source data; biological hazard cannot be assumed or fabricated.")
            thoughts.append(self.log_thought(
                "UNSPECIFIED_EXPIRY",
                "Product has no recorded expiry date. Marking shelf-life status as Unspecified."
            ))
            
            risk_metrics = {
                "risk_level": "UNKNOWN",
                "urgency_score": 0,
                "expected_surplus_units": 0.0,
                "expected_spoiled_units": 0.0,
                "spoilage_probability": 0.0,
                "financial_risk_usd": 0.0,
                "carbon_risk_kg": 0.0,
                "shelf_life_status": "Unspecified Expiry"
            }

            recommendation = self.create_recommendation(
                product=batch_data,
                proposed_action="MONITOR_EXPIRY",
                action_title="Monitor Stock (Expiry Date Unspecified)",
                supporting_evidence={
                    "current_stock": stock,
                    "days_to_expiry": None,
                    "risk_level": "UNKNOWN"
                },
                priority="LOW",
                explanation="No biological hazard identified because expiry date is unrecorded. Continued standard retail monitoring recommended.",
                missing_information_or_assumptions=assumptions,
                confidence=0.50
            )

            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "risk_metrics": risk_metrics,
                "recommendation": recommendation,
                "missing_information_or_assumptions": assumptions,
                "thoughts": thoughts
            }

        dte = int(raw_dte)
        thoughts.append(self.log_thought(
            "EVALUATE_HAZARD",
            f"Checking storage telemetry: Actual {actual_temp}°C vs Target {target_temp}°C. Current inventory: {stock} units, Days to expiry: {dte}d."
        ))

        risk_metrics = self.risk_evaluator.evaluate_batch_risk(
            current_stock=stock,
            days_to_expiry=dte,
            cumulative_demand_p50=cum_demand,
            unit_cost=unit_cost,
            base_price=base_price,
            carbon_factor_kg=carbon_factor,
            actual_temp_c=actual_temp,
            target_temp_c=target_temp
        )

        expected_spoiled = risk_metrics["expected_spoiled_units"]
        surplus = risk_metrics["expected_surplus_units"]
        financial_risk = risk_metrics["financial_risk_usd"]
        carbon_risk = risk_metrics["carbon_risk_kg"]

        # Classify freshness priority
        if dte <= self.policy.freshness.expired_threshold_days:
            priority = "CRITICAL"
            action = "EXPIRED_FLAGGED"
            action_title = f"Product Expired / Due Today ({stock} units at risk)"
            explanation = f"Product has reached or passed expiry (DTE: {dte}d). Immediate diversion (Food Bank donation or compost) is mandatory to prevent waste."
        elif dte <= self.policy.freshness.critical_expiry_days:
            priority = "CRITICAL"
            action = "URGENT_EXPIRY_RISK"
            action_title = f"Critical Shelf-Life Expiry in 24h ({surplus}u surplus)"
            explanation = f"Product expires within 24 hours. Expected unconsumed surplus is {surplus:.1f} units ($ {financial_risk:.2f} at cost)."
        elif dte <= self.policy.freshness.urgent_expiry_days:
            priority = "HIGH"
            action = "EXPIRING_SOON"
            action_title = f"At-Risk Expiry in 48h ({surplus}u surplus)"
            explanation = f"Product expires in 2 days. Stock ({stock}u) exceeds remaining shelf-life demand ({cum_demand:.1f}u)."
        elif dte <= self.policy.freshness.warning_expiry_days:
            priority = "MEDIUM"
            action = "EXPIRY_WARNING"
            action_title = f"Moderate Expiry Window ({dte} days remaining)"
            explanation = f"Product has {dte} days remaining. Velocity should be monitored to avoid late-stage waste."
        else:
            priority = "LOW"
            action = "FRESH_NOMINAL"
            action_title = f"Fresh Inventory ({dte} days remaining)"
            explanation = f"Product shelf-life is healthy ({dte} days remaining). Biological decay risk is minimal."

        thoughts.append(self.log_thought(
            "COMPUTE_DEFICIT",
            f"Risk Tier: {risk_metrics['risk_level']} (Urgency: {risk_metrics['urgency_score']}/100). "
            f"Expected Spoilage: {expected_spoiled} units ($ {financial_risk} at cost, {carbon_risk} kg CO2e potential footprint)."
        ))

        recommendation = self.create_recommendation(
            product=batch_data,
            proposed_action=action,
            action_title=action_title,
            supporting_evidence={
                "current_stock": stock,
                "days_to_expiry": dte,
                "expected_surplus_units": surplus,
                "expected_spoiled_units": expected_spoiled,
                "financial_risk_usd": financial_risk,
                "carbon_risk_kg": carbon_risk,
                "storage_temp_c": actual_temp,
                "target_temp_c": target_temp
            },
            priority=priority,
            explanation=explanation,
            missing_information_or_assumptions=assumptions,
            confidence=0.92
        )

        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "risk_metrics": risk_metrics,
            "recommendation": recommendation,
            "missing_information_or_assumptions": assumptions,
            "thoughts": thoughts
        }

# Aliases for backward compatibility
SpoilageRiskAgent = FreshnessAgent
