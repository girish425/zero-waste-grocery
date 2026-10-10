"""
Optional LLM Explanation Synthesizer
Zero-Waste Grocery · GDGoC HITAM

Enforces core Agentic AI governance:
- Deterministic explainers by default (zero dependency on paid APIs)
- If an LLM is optionally configured, it explains existing evidence in plain language
- STRICT RULE: The LLM must not invent data or override validation results
"""
from typing import Dict, Any, Optional

def explain_recommendation_in_plain_language(
    recommendation: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = "gemini-1.5-flash"
) -> str:
    """
    Synthesizes a plain-language executive explanation from structured evidence.
    Falls back deterministically to rule-based template if API key is absent.
    """
    prod = recommendation.get("product", {})
    p_name = prod.get("product_name", "Perishable Item")
    store = prod.get("store_name", "Store")
    action = recommendation.get("proposed_action", "MAINTAIN")
    evidence = recommendation.get("supporting_evidence", {})
    assumptions = recommendation.get("missing_information_or_assumptions", [])
    priority = recommendation.get("priority", "MEDIUM")

    # If an API key is provided, attempt optional generative synthesis with strict grounding
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            prompt = f"""
You are the AI Auditor for Zero-Waste Grocery. Explain the following decision for store planners in 2 concise sentences.
STRICT RULES:
1. Base your explanation ONLY on the provided evidence.
2. DO NOT invent dates, numbers, or assumptions not listed below.
3. DO NOT override the proposed action or priority.

Product: {p_name} ({prod.get('sku', '')}) at {store}
Proposed Action: {action} (Priority: {priority})
Evidence: {evidence}
Missing Data / Assumptions: {assumptions}
"""
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            # Fall back safely to deterministic generator on any network or API issue
            pass

    # Deterministic Rule-Based Explainer (100% Free, Reliable & Grounded)
    dte = evidence.get("days_to_expiry")
    stock = evidence.get("current_stock") or evidence.get("stock", 0)

    if action == "DONATE":
        return f"{p_name} at {store} has reached its final shelf day with {stock} units on hand. Directing to food bank partners preserves nutritional value and diverts food from landfills."
    elif action == "MARKDOWN":
        disc = evidence.get("discount_pct", 20)
        p_disc = evidence.get("discounted_price", 0)
        return f"A dynamic {disc}% markdown (${p_disc:.2f}) is proposed for {p_name} at {store} to stimulate consumer sell-through before expiry (DTE: {dte}d) and recover margin."
    elif action == "TRANSFER":
        dest = evidence.get("destination_store", "Sister Store")
        qty = evidence.get("transfer_qty", stock)
        return f"Rebalancing {qty} units of {p_name} from {store} to {dest} captures full retail price in a high-turnover location, generating higher salvage than local discounting."
    elif action == "REORDER":
        qty = evidence.get("recommended_order_qty", 10)
        rop = evidence.get("reorder_point", 10)
        return f"On-shelf inventory ({stock}u) for {p_name} at {store} breached the safety reorder threshold ({rop}u). Issuing PO for {qty} units prevents stockouts without risking spoilage."
    elif action == "HOLD_REORDER":
        return f"Replenishment is held for {p_name} at {store} because impending batch expiry or unrecorded velocity requires resolving current stock before acquiring new units."
    else:
        return f"{p_name} at {store} exhibits nominal stock velocity matching demand expectations. Standard inventory monitoring continues without intervention."
