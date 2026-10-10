"""
Base Agent Architecture for Zero-Waste Grocery
Multi-Agent Orchestration Architecture with Reasoning Trace & Structured Recommendations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

class BaseGroceryAgent:
    """
    Base Agent with reasoning chain capture, telemetry, and structured outputs.
    """
    def __init__(self, agent_id: str, name: str, role: str, color_hex: str = "#7C3AED"):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.color_hex = color_hex
        
    def log_thought(self, step: str, thought: str) -> Dict[str, str]:
        """Creates a structured thought record for Explainable AI (XAI) auditing."""
        return {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "step": step,
            "thought": thought
        }

    def create_recommendation(
        self,
        product: Dict[str, Any],
        proposed_action: str,
        action_title: str,
        supporting_evidence: Dict[str, Any],
        priority: str,
        explanation: str,
        missing_information_or_assumptions: Optional[List[str]] = None,
        confidence: float = 0.90,
        extra_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Creates a canonical, structured agent recommendation.
        Guarantees that product, proposed action, supporting evidence, priority,
        and missing information/assumptions are explicitly present.
        """
        rec = {
            "generating_agent": self.name,
            "agent_id": self.agent_id,
            "product": {
                "sku": str(product.get("sku", "UNKNOWN_SKU")),
                "product_name": str(product.get("product_name", "Unknown Product")),
                "store_id": str(product.get("store_id", "STORE-01")),
                "store_name": str(product.get("store_name", "Primary Store")),
                "category": str(product.get("category", "General")),
            },
            "proposed_action": proposed_action,
            "action_title": action_title,
            "priority": priority, # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
            "supporting_evidence": supporting_evidence or {},
            "missing_information_or_assumptions": missing_information_or_assumptions or [],
            "explanation": explanation,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        if extra_details:
            rec.update(extra_details)
        return rec
