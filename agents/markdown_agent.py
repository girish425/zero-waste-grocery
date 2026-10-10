"""
Dynamic Markdown & Pricing Agent (Compatibility Module)
Re-exports DiscountAgent from agents.discount_agent.
Zero-Waste Grocery · GDGoC HITAM
"""
from agents.discount_agent import DiscountAgent, MarkdownPricingAgent

__all__ = ["DiscountAgent", "MarkdownPricingAgent"]
