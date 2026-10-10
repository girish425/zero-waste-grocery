"""
Shelf-Life & Spoilage Risk Agent (Compatibility Module)
Re-exports FreshnessAgent from agents.freshness_agent.
Zero-Waste Grocery · GDGoC HITAM
"""
from agents.freshness_agent import FreshnessAgent, SpoilageRiskAgent

__all__ = ["FreshnessAgent", "SpoilageRiskAgent"]
