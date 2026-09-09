from typing import List, Dict, Any
from tensormesh.ml.ranking_engine import SupplierRankingEngine

class DeterministicReplaySimulator:
    def __init__(self):
        self.ranker = SupplierRankingEngine()

    def run_policy_shock_simulation(self, historical_suppliers: List[Dict], shock_scenario: str) -> Dict[str, Any]:
        """
        Replays historical supply chain data against a new geopolitical shock.
        """
        print(f"\n[Simulator] Initiating 'What-If' Scenario: {shock_scenario}")
        
        # Apply the shock to the historical data
        simulated_suppliers = []
        for sup in historical_suppliers:
            sim_sup = sup.copy()
            if shock_scenario == "CHINA_EXPORT_BAN" and sim_sup["china_ownership"] > 0:
                sim_sup["lead_time"] += 90 # Add 3 months of delay
                sim_sup["geo_risk"] = 1.0  # Maximize risk
            simulated_suppliers.append(sim_sup)
            
        # Re-rank based on the new simulated reality
        new_ranking = self.ranker.rank_suppliers(simulated_suppliers, intent_profile="defense")
        
        return {
            "scenario": shock_scenario,
            "new_top_supplier": new_ranking[0]["name"],
            "new_rankings": new_ranking
        }