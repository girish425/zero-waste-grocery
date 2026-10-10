"""
Inter-Store Inventory Transfer Agent
Identifies network-wide demand imbalances and recommends intra-store balancing transfers.
Zero-Waste Grocery · GDGoC HITAM
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from agents.base_agent import BaseGroceryAgent
from agents.config import AgentWorkflowPolicy, StoreTransferPolicy
from data.store_data import STORES

class StoreTransferAgent(BaseGroceryAgent):
    """
    Store Transfer Agent:
    Suggests moving inventory between stores ONLY when multiple store locations
    and comparable inventory data exist, transit logistics are feasible, and net salvage is positive.
    """
    def __init__(self, policy: Optional[AgentWorkflowPolicy] = None):
        super().__init__(
            agent_id="AGENT-TRANSFER-05",
            name="Inter-Store Transfer Agent",
            role="Cross-Store Network Balancing & Re-allocation",
            color_hex="#6B21A8"
        )
        self.policy = policy or AgentWorkflowPolicy()

    def evaluate(
        self,
        batch_data: Dict[str, Any],
        all_inventory_df: Optional[pd.DataFrame] = None,
        freshness_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Scans network to identify high-velocity recipient stores that can sell expiring stock at full price.
        Enforces strict multi-store and shelf-life constraints.
        """
        thoughts = []
        assumptions = []
        source_store_id = str(batch_data.get("store_id", "STORE-01"))
        source_store_name = str(batch_data.get("store_name", "Primary Store"))
        sku = str(batch_data.get("sku", "UNKNOWN_SKU"))
        raw_dte = batch_data.get("days_to_expiry")
        base_price = float(batch_data.get("base_price", 0.0))
        unit_cost = float(batch_data.get("unit_cost", 0.0))
        
        transfer_policy: StoreTransferPolicy = getattr(self.policy, "transfer", StoreTransferPolicy())

        # Determine surplus units
        if freshness_output and "risk_metrics" in freshness_output:
            surplus = float(freshness_output["risk_metrics"].get("expected_surplus_units", 0.0))
        else:
            stock = float(batch_data.get("current_stock", 0))
            surplus = max(0.0, stock * 0.4)

        # 1. Multi-Store Availability Constraint: "Do not create transfer suggestions without multiple stores"
        store_col = None
        unique_stores_count = 0
        if all_inventory_df is not None and not all_inventory_df.empty:
            for cand in ["store_id", "store_name", "store", "branch_id"]:
                if cand in all_inventory_df.columns:
                    store_col = cand
                    unique_stores_count = all_inventory_df[cand].nunique()
                    break

        if transfer_policy.require_multiple_stores and unique_stores_count <= 1:
            reason = (
                f"Inter-store transfer cannot be evaluated: Single store location exists in the active dataset ({unique_stores_count} store found). "
                "Cross-store inventory rebalancing strictly requires multiple store locations."
            )
            assumptions.append("Dataset contains a single store location; transfer candidate evaluation was bypassed.")
            thoughts.append(self.log_thought("SINGLE_STORE_NETWORK", reason))

            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_TRANSFER",
                action_title="No Transfer (Single Store Network)",
                supporting_evidence={
                    "stores_detected": unique_stores_count,
                    "multi_store_available": False
                },
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=1.0
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_TRANSFER", "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": assumptions,
                "thoughts": thoughts
            }

        # 2. Expiry & Shelf-Life Transit Logistics Check
        if raw_dte is None or pd.isna(raw_dte):
            reason = "Expiry date is unspecified in source data; cannot route refrigerated transit without verified shelf-life."
            assumptions.append("Expiry date unspecified; transit logistics withheld.")
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_TRANSFER",
                action_title="No Transfer (Expiry Date Unspecified)",
                supporting_evidence={"days_to_expiry": None},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.85
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_TRANSFER", "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": assumptions,
                "thoughts": [self.log_thought("UNSPECIFIED_EXPIRY", reason)]
            }

        dte = int(raw_dte)
        if dte < transfer_policy.min_shelf_life_days:
            reason = (
                f"Insufficient remaining shelf-life window ({dte} days left). "
                f"Transit logistics and cold-chain re-shelving require at least {transfer_policy.min_shelf_life_days} days."
            )
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_TRANSFER",
                action_title="No Transfer (Insufficient Transit Window)",
                supporting_evidence={"days_to_expiry": dte, "min_required_days": transfer_policy.min_shelf_life_days},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=[],
                confidence=0.92
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_TRANSFER", "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": [],
                "thoughts": [self.log_thought("TRANSIT_NOT_FEASIBLE", reason)]
            }

        # 3. Minimum Surplus Check
        if surplus < transfer_policy.min_surplus_units:
            reason = f"Surplus ({surplus:.1f} units) is below minimum freight threshold ({transfer_policy.min_surplus_units} units)."
            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="NO_TRANSFER",
                action_title="No Transfer (Surplus Below Freight Threshold)",
                supporting_evidence={"surplus_units": surplus, "min_surplus_threshold": transfer_policy.min_surplus_units},
                priority="LOW",
                explanation=reason,
                missing_information_or_assumptions=[],
                confidence=0.90
            )
            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": {"action": "NO_TRANSFER", "reasoning": reason},
                "recommendation": rec,
                "missing_information_or_assumptions": [],
                "thoughts": [self.log_thought("LOW_SURPLUS", reason)]
            }

        thoughts.append(self.log_thought(
            "SCAN_NETWORK",
            f"Scanning {unique_stores_count - 1} sister stores for SKU {sku} with surplus {surplus:.1f} units."
        ))

        # 4. Scan Network for High-Velocity Recipient Stores with Low Coverage
        candidates = []
        sku_inv = all_inventory_df[all_inventory_df["sku"].astype(str) == sku] if "sku" in all_inventory_df.columns else pd.DataFrame()

        # Identify other stores from all_inventory_df
        other_store_ids = [s for s in all_inventory_df[store_col].unique() if str(s) != source_store_id]
        
        for other_id in other_store_ids:
            other_id_str = str(other_id)
            other_batches = sku_inv[sku_inv[store_col].astype(str) == other_id_str] if not sku_inv.empty else pd.DataFrame()
            other_stock = float(other_batches["current_stock"].sum()) if ("current_stock" in other_batches.columns and not other_batches.empty) else 0.0
            
            # Daily sales at other store
            if not other_batches.empty and "avg_daily_sales" in other_batches.columns and pd.notnull(other_batches["avg_daily_sales"].iloc[0]):
                other_daily_sales = float(other_batches["avg_daily_sales"].iloc[0])
            else:
                other_daily_sales = 8.0 # Default benchmark
                assumptions.append(f"Sales velocity at sister store {other_id_str} was unrecorded; used network benchmark.")

            days_cover = other_stock / max(1.0, other_daily_sales)

            # Recipient must have low coverage (< max_recipient_days_cover)
            if days_cover < transfer_policy.max_recipient_days_cover:
                # Distance calculation
                dist_km = 15.0
                if source_store_id in STORES and other_id_str in STORES:
                    dist_km = abs(STORES[other_id_str]["distance_to_hub_km"] - STORES[source_store_id]["distance_to_hub_km"]) + 8.0
                
                transit_cost = round(transfer_policy.transit_cost_per_unit * surplus + transfer_policy.transit_cost_per_km * dist_km, 2)
                net_salvage = round(surplus * (base_price - unit_cost) - transit_cost, 2)

                # Store display name
                dest_name = STORES.get(other_id_str, {}).get("name", f"Store {other_id_str}")
                if "store_name" in other_batches.columns and not other_batches.empty:
                    dest_name = str(other_batches["store_name"].iloc[0])

                if net_salvage > 0:
                    candidates.append({
                        "dest_store_id": other_id_str,
                        "dest_store_name": dest_name,
                        "dest_stock": other_stock,
                        "dest_daily_sales": round(other_daily_sales, 1),
                        "days_cover": round(days_cover, 1),
                        "distance_km": round(dist_km, 1),
                        "transit_cost_usd": transit_cost,
                        "net_salvage_usd": net_salvage
                    })

        if candidates:
            best_dest = sorted(candidates, key=lambda x: x["net_salvage_usd"], reverse=True)[0]
            transfer_qty = int(min(surplus, max(5, round(best_dest["dest_daily_sales"] * 1.5))))

            reason = (
                f"Rebalance {transfer_qty} units from {source_store_name} to {best_dest['dest_store_name']} ({best_dest['distance_km']} km). "
                f"Recipient has high velocity ({best_dest['dest_daily_sales']} u/day) and low cover ({best_dest['days_cover']} days). "
                f"Can be sold at full retail price (${base_price:.2f}), yielding net salvage of ${best_dest['net_salvage_usd']:.2f} after ${best_dest['transit_cost_usd']:.2f} transit cost."
            )

            thoughts.append(self.log_thought(
                "MATCH_FOUND",
                f"Candidate {best_dest['dest_store_name']} has high turnover ({best_dest['dest_daily_sales']} units/day). "
                f"Dispatching {transfer_qty} units across {best_dest['distance_km']} km."
            ))

            proposal = {
                "action": "INTER_STORE_TRANSFER",
                "transfer_qty": transfer_qty,
                "destination_store_id": best_dest["dest_store_id"],
                "destination_store_name": best_dest["dest_store_name"],
                "transit_cost_usd": best_dest["transit_cost_usd"],
                "projected_salvage_usd": best_dest["net_salvage_usd"],
                "urgency": "HIGH",
                "confidence": 0.86,
                "reasoning": reason
            }

            rec = self.create_recommendation(
                product=batch_data,
                proposed_action="TRANSFER",
                action_title=f"Transfer {transfer_qty} units to {best_dest['dest_store_name']}",
                supporting_evidence={
                    "source_store": source_store_name,
                    "destination_store": best_dest["dest_store_name"],
                    "transfer_qty": transfer_qty,
                    "transit_distance_km": best_dest["distance_km"],
                    "transit_cost_usd": best_dest["transit_cost_usd"],
                    "projected_salvage_usd": best_dest["net_salvage_usd"],
                    "destination_turnover_rate": best_dest["dest_daily_sales"],
                    "destination_days_cover": best_dest["days_cover"]
                },
                priority="HIGH",
                explanation=reason,
                missing_information_or_assumptions=assumptions,
                confidence=0.86
            )

            return {
                "agent": self.name,
                "agent_id": self.agent_id,
                "proposal": proposal,
                "recommendation": rec,
                "missing_information_or_assumptions": assumptions,
                "thoughts": thoughts
            }

        reason = "No candidate sister store in the network currently exhibits a critical stock deficit with positive net salvage."
        rec = self.create_recommendation(
            product=batch_data,
            proposed_action="NO_TRANSFER",
            action_title="No Transfer Candidate Found",
            supporting_evidence={"network_stores_scanned": len(other_store_ids), "viable_candidates": 0},
            priority="LOW",
            explanation=reason,
            missing_information_or_assumptions=assumptions,
            confidence=0.88
        )
        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "proposal": {"action": "NO_TRANSFER", "reasoning": reason},
            "recommendation": rec,
            "missing_information_or_assumptions": assumptions,
            "thoughts": [self.log_thought("NO_CANDIDATE", reason)]
        }

# Alias for backward compatibility
InventoryTransferAgent = StoreTransferAgent
