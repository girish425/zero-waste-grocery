"""
Demand Forecasting Agent
Specialized agent for consumer velocity projection, elasticity, and seasonal patterns.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
from datetime import date
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy
from models.forecaster import PerishableDemandForecaster

class DemandAgent(BaseGroceryAgent):
    """
    Demand Agent:
    Analyzes historical sales transactions, velocity, day-of-week seasonality,
    and projects perishable demand across remaining shelf-life horizons.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-DEMAND-01",
            name="Demand Forecaster Agent",
            role="Perishable Velocity & Seasonal Demand Modeling",
            color_hex="#0284C7"
        )
        self.policy = policy or AgentWorkflowPolicy()
        self.forecaster = PerishableDemandForecaster()

    def evaluate(
        self,
        batch_data: Dict[str, Any],
        sales_df: Optional[pd.DataFrame] = None,
        temp_delta_c: float = 0.0
    ) -> Dict[str, Any]:
        """
        Analyzes batch context and projects expected demand until expiry date.
        """
        thoughts = []
        assumptions = []
        sku = batch_data.get("sku", "UNKNOWN_SKU")
        product_name = batch_data.get("product_name", "Unknown Product")
        category = batch_data.get("category", "General")
        raw_vel = batch_data.get("avg_daily_sales")
        stock = float(batch_data.get("current_stock", 0))

        # Check whether sales velocity was provided in dataset
        if raw_vel is None or pd.isna(raw_vel) or (hasattr(raw_vel, "__len__") and len(raw_vel) == 0):
            # Do NOT fabricate historical sales! Document assumption explicitly
            base_velocity = max(1.0, stock / 4.0)
            assumptions.append("Sales velocity was unrecorded in uploaded data; initialized a conservative baseline runway of 4 days.")
            thoughts.append(self.log_thought(
                "UNRECORDED_VELOCITY",
                f"Sales velocity unrecorded for {sku}; initialized nominal runway baseline ({base_velocity:.1f} u/day)."
            ))
        else:
            base_velocity = float(raw_vel)
            thoughts.append(self.log_thought(
                "INGEST_VELOCITY",
                f"Analyzing historical sales velocity for {sku} ({product_name}): {base_velocity:.1f} units/day."
            ))

        raw_dte = batch_data.get("days_to_expiry")
        has_verified_expiry = raw_dte is not None and not pd.isna(raw_dte)
        if not has_verified_expiry:
            days_to_expiry = 7
            assumptions.append("Product expiry date was unspecified; evaluated demand over a standard 7-day planning horizon.")
        else:
            days_to_expiry = max(1, int(raw_dte))

        current_date = date.today()
        horizon = min(7, max(1, days_to_expiry))

        fc_df = self.forecaster.generate_horizon_forecast(
            base_daily_sales=base_velocity,
            start_date=current_date,
            horizon_days=horizon,
            category=category,
            temp_delta_c=temp_delta_c
        )

        cumulative_demand = float(fc_df["forecast_p50"].sum())
        p10_sum = float(fc_df["forecast_p10"].sum())
        p90_sum = float(fc_df["forecast_p90"].sum())

        thoughts.append(self.log_thought(
            "PROJECT_HORIZON",
            f"Projected cumulative demand over {horizon} remaining shelf days: P50={round(cumulative_demand, 1)} units "
            f"(80% CI: {round(p10_sum, 1)} to {round(p90_sum, 1)} units)."
        ))

        explanation = (
            f"Forecasted expected consumption of {round(cumulative_demand, 1)} units over the next {horizon} day(s) "
            f"(daily rate: {base_velocity:.1f} u/day). Estimated 80% confidence interval ranges from {round(p10_sum, 1)} to {round(p90_sum, 1)} units."
        )

        recommendation = self.create_recommendation(
            product=batch_data,
            proposed_action="FORECAST_UPDATED",
            action_title=f"Demand Projection: {round(cumulative_demand, 1)} units ({horizon}d)",
            supporting_evidence={
                "base_daily_velocity": round(base_velocity, 1),
                "horizon_days": horizon,
                "cumulative_demand_p50": round(cumulative_demand, 1),
                "confidence_p10": round(p10_sum, 1),
                "confidence_p90": round(p90_sum, 1)
            },
            priority="LOW",
            explanation=explanation,
            missing_information_or_assumptions=assumptions,
            confidence=0.88 if not assumptions else 0.70
        )

        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "base_velocity": round(base_velocity, 1),
            "cumulative_demand_p50": round(cumulative_demand, 1),
            "p10_confidence": round(p10_sum, 1),
            "p90_confidence": round(p90_sum, 1),
            "daily_forecast_df": fc_df,
            "recommendation": recommendation,
            "missing_information_or_assumptions": assumptions,
            "thoughts": thoughts
        }

# Backward compatibility alias
DemandForecastingAgent = DemandAgent
