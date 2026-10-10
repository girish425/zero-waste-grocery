"""
Shelf-Life & Biological Spoilage Risk Model
Estimates spoilage probability, inventory hazard decay curves, and financial/carbon loss potential.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any

class SpoilageRiskEvaluator:
    """
    Biological and probabilistic shelf-life evaluation model.
    Models the perishable hazard rate as a function of:
    1. Days remaining until expiry date
    2. Cold chain temperature compliance (Arrhenius spoilage acceleration)
    3. Ratio of current stock to forecasted demand window
    """
    
    def __init__(self):
        pass

    def evaluate_batch_risk(
        self,
        current_stock: int,
        days_to_expiry: int,
        cumulative_demand_p50: float,
        unit_cost: float,
        base_price: float,
        carbon_factor_kg: float,
        actual_temp_c: float = 4.0,
        target_temp_c: float = 4.0
    ) -> Dict[str, Any]:
        """
        Computes comprehensive spoilage risk metrics for an individual batch.
        """
        # 1. Check if expiry date is unspecified - DO NOT ASSUME OR FABRICATE EXPIRY RISK
        if days_to_expiry is None or pd.isna(days_to_expiry):
            return {
                "risk_level": "UNKNOWN",
                "urgency_score": 0,
                "spoilage_probability": 0.0,
                "expected_surplus_units": 0.0,
                "expected_spoiled_units": 0.0,
                "financial_risk_usd": 0.0,
                "lost_revenue_potential": 0.0,
                "carbon_risk_kg": 0.0,
                "stock_coverage_ratio": 1.0,
                "thermal_decay_factor": 1.0,
                "is_unspecified_expiry": True
            }

        # 2. Thermal degradation multiplier (Arrhenius approximation: Q10 ~ 2.0 per 10°C delta)
        temp_delta = max(0.0, actual_temp_c - target_temp_c)
        thermal_decay_factor = 1.0 + (0.08 * temp_delta)
        
        # Effective adjusted days left if cold chain had mild breaches
        effective_days = max(0.2, days_to_expiry / thermal_decay_factor)
        
        # 2. Demand vs Stock Deficit Calculation
        # How many units will remain unsold when expiry date is reached?
        expected_surplus = max(0.0, current_stock - cumulative_demand_p50)
        stock_coverage_ratio = cumulative_demand_p50 / max(1.0, float(current_stock))
        
        # 3. Spoilage Probability Calculation
        if days_to_expiry <= 0:
            spoilage_prob = 1.0
        elif days_to_expiry == 1:
            if expected_surplus > 0:
                spoilage_prob = min(0.98, max(0.40, (expected_surplus / current_stock) * 1.1))
            else:
                spoilage_prob = 0.15 # Small probability of customer rejection
        elif days_to_expiry == 2:
            spoilage_prob = min(0.85, max(0.15, (expected_surplus / current_stock) * 0.9))
        else:
            # Further out: hazard depends on mismatch
            spoilage_prob = min(0.65, max(0.02, (expected_surplus / current_stock) * 0.5))
            
        spoilage_prob = round(float(np.clip(spoilage_prob, 0.0, 1.0)), 3)
        
        # 4. Projected Losses
        expected_spoiled_units = round(expected_surplus * min(1.0, spoilage_prob * 1.2), 1)
        expected_spoiled_units = min(float(current_stock), expected_spoiled_units)
        
        financial_risk_usd = round(expected_spoiled_units * unit_cost, 2)
        lost_revenue_potential = round(expected_spoiled_units * base_price, 2)
        carbon_footprint_risk_kg = round(expected_spoiled_units * carbon_factor_kg, 2)
        
        # 5. Risk Categorization
        if days_to_expiry <= 1 and expected_surplus > 1:
            risk_level = "CRITICAL"
            urgency_score = 95
        elif days_to_expiry <= 2 and expected_surplus > 2:
            risk_level = "HIGH"
            urgency_score = 75
        elif expected_surplus > 5:
            risk_level = "MEDIUM"
            urgency_score = 50
        else:
            risk_level = "LOW"
            urgency_score = 15
            
        return {
            "risk_level": risk_level,
            "urgency_score": urgency_score,
            "spoilage_probability": spoilage_prob,
            "expected_surplus_units": round(expected_surplus, 1),
            "expected_spoiled_units": expected_spoiled_units,
            "financial_risk_usd": financial_risk_usd,
            "lost_revenue_potential": lost_revenue_potential,
            "carbon_risk_kg": carbon_footprint_risk_kg,
            "stock_coverage_ratio": round(stock_coverage_ratio, 2),
            "thermal_decay_factor": round(thermal_decay_factor, 2)
        }
        
    def generate_decay_curve(self, nominal_days: int, current_age_days: int) -> Dict[str, Any]:
        """
        Generates non-linear Weibull quality decay curve for visualization.
        """
        days = np.linspace(0, nominal_days + 1, 30)
        # Weibull survival function S(t) = exp(-(t/lambda)^k)
        scale = nominal_days * 0.95
        shape = 2.4
        survival = np.exp(-((days / scale) ** shape)) * 100.0
        
        return {
            "timeline_days": [round(d, 1) for d in days],
            "quality_index": [round(s, 1) for s in survival]
        }
