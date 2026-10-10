"""
Agent Workflow Configuration and Business Policies
Zero-Waste Grocery · GDGoC HITAM

Provides configurable thresholds, policies, and constraints for:
- Freshness evaluation (expiry warning windows, biological hazard)
- Discount & markdown pricing (elasticity, markdown tiers, enable/disable)
- Replenishment & reordering (service level, safety stock, lead times)
- Inter-store transfers (minimum stores, minimum shelf life, transit costs)
- Optional LLM natural language explainers
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class FreshnessPolicy:
    """Configurable thresholds for product freshness and expiry risk."""
    expired_threshold_days: int = 0      # <= 0 days: Expired / Due Today
    critical_expiry_days: int = 1        # <= 1 day: Urgent / Immediate Action
    urgent_expiry_days: int = 2          # <= 2 days: At-Risk Shelf Window
    warning_expiry_days: int = 4         # <= 4 days: Watchlist Window
    default_storage_temp_c: float = 4.0  # Cold-chain baseline

@dataclass
class DiscountPolicy:
    """Configurable policy for price elasticity and markdown tiers."""
    enabled: bool = True                 # Whether markdown pricing is permitted
    max_discount_pct: int = 60           # Maximum allowable promotional discount
    default_tiers: Dict[int, int] = field(default_factory=lambda: {
        0: 60,   # Expiring today: 60% flash clearance
        1: 40,   # 1 day left: 40% urgent markdown
        2: 25,   # 2 days left: 25% dynamic discount
        3: 15    # 3+ days left: 15% preventive discount
    })
    price_elasticity: float = -1.35      # Empirical perishable price elasticity epsilon
    min_surplus_units: float = 1.0       # Minimum excess stock required to trigger discount

@dataclass
class ReplenishmentPolicy:
    """Configurable policy for inventory replenishment and safety stock."""
    target_service_level_z: float = 1.65 # Z = 1.65 corresponds to 95% cycle service level
    default_lead_time_days: int = 2      # Supplier delivery lead time
    target_days_cover: float = 3.5       # Target stock runway in days
    min_order_qty: int = 10              # Minimum procurement order size
    suppress_on_critical_spoilage: bool = True # Block reorders if batch is spoiling

@dataclass
class StoreTransferPolicy:
    """Configurable policy for network-wide balancing transfers."""
    min_shelf_life_days: int = 2         # Transit logistics require >= 2 days remaining
    min_surplus_units: float = 3.0       # Minimum excess units to justify freight
    max_recipient_days_cover: float = 3.0# Recipient store must have < 3 days coverage
    transit_cost_per_km: float = 0.15    # Transport fuel / mileage cost per km
    transit_cost_per_unit: float = 0.12  # Handling / packaging cost per unit
    require_multiple_stores: bool = True # Strictly require >= 2 stores to propose transfer

@dataclass
class AgentWorkflowPolicy:
    """
    Master configurable workflow policy uniting all specialist agents.
    Can be instantiated with custom parameters for testing and operational adaptation.
    """
    freshness: FreshnessPolicy = field(default_factory=FreshnessPolicy)
    discount: DiscountPolicy = field(default_factory=DiscountPolicy)
    replenishment: ReplenishmentPolicy = field(default_factory=ReplenishmentPolicy)
    transfer: StoreTransferPolicy = field(default_factory=StoreTransferPolicy)
    llm_enabled: bool = False
    llm_api_key: Optional[str] = None
    llm_model: str = "gemini-1.5-flash"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes policy for audit records and XAI inspection."""
        return {
            "freshness": {
                "critical_days": self.freshness.critical_expiry_days,
                "warning_days": self.freshness.warning_expiry_days,
            },
            "discount": {
                "enabled": self.discount.enabled,
                "max_discount_pct": self.discount.max_discount_pct,
                "elasticity": self.discount.price_elasticity,
            },
            "replenishment": {
                "service_level_z": self.replenishment.target_service_level_z,
                "default_lead_time": self.replenishment.default_lead_time_days,
            },
            "transfer": {
                "min_shelf_life_days": self.transfer.min_shelf_life_days,
                "require_multiple_stores": self.transfer.require_multiple_stores,
            },
            "llm_enabled": self.llm_enabled
        }
