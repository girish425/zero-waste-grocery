"""
Agents package for Zero-Waste Grocery
Provides the 6 specialized autonomous agents, configuration policies, and coordination arbiters:
1. Demand Agent (DemandAgent / DemandForecastingAgent)
2. Freshness Agent (FreshnessAgent / SpoilageRiskAgent)
3. Discount Agent (DiscountAgent / MarkdownPricingAgent)
4. Replenishment Agent (ReplenishmentAgent)
5. Store Transfer Agent (StoreTransferAgent / InventoryTransferAgent)
6. Chief Coordinator Agent (CoordinatorAgent)
"""
from agents.base_agent import BaseGroceryAgent
from agents.config import (
    AgentWorkflowPolicy,
    FreshnessPolicy,
    DiscountPolicy,
    ReplenishmentPolicy,
    StoreTransferPolicy
)
from agents.demand_agent import DemandAgent, DemandForecastingAgent
from agents.freshness_agent import FreshnessAgent, SpoilageRiskAgent
from agents.discount_agent import DiscountAgent, MarkdownPricingAgent
from agents.replenishment_agent import ReplenishmentAgent
from agents.transfer_agent import StoreTransferAgent, InventoryTransferAgent
from agents.coordinator import CoordinatorAgent
from agents.llm_explainer import explain_recommendation_in_plain_language

__all__ = [
    "BaseGroceryAgent",
    "AgentWorkflowPolicy",
    "FreshnessPolicy",
    "DiscountPolicy",
    "ReplenishmentPolicy",
    "StoreTransferPolicy",
    "DemandAgent",
    "DemandForecastingAgent",
    "FreshnessAgent",
    "SpoilageRiskAgent",
    "DiscountAgent",
    "MarkdownPricingAgent",
    "ReplenishmentAgent",
    "StoreTransferAgent",
    "InventoryTransferAgent",
    "CoordinatorAgent",
    "explain_recommendation_in_plain_language"
]
