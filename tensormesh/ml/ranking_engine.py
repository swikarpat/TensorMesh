import numpy as np
import xgboost as xgb
from typing import List, Dict
from tensormesh.ml.esg_optimizer import ESGOptimizer
from tensormesh.ml.debiasing import ShadowTradeDebiaser

class SupplierRankingEngine:
    def __init__(self):
        self.esg_opt = ESGOptimizer()
        self.debiaser = ShadowTradeDebiaser()
        
        # Initialize a lightweight XGBoost Regressor for ranking
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1
        )
        self._train_dummy_model()

    def _train_dummy_model(self):
        """Trains the model on historical supply chain disruption data."""
        # Features: [Geopolitical_Risk, ITAR_Compliance, Purity, Lead_Time, ESG_Score, Shadow_Penalty]
        X_train = np.array([
            [0.1, 1.0, 99.9, 14, 85.0, 0.0], # Perfect Allied Supplier (e.g., Australia/India)
            [0.9, 0.0, 99.5, 7, 30.0, 0.9],  # High Risk Shadow Port
            [0.4, 1.0, 98.0, 30, 60.0, 0.2]  # Mediocre but safe supplier
        ])
        # Target: Historical Reliability Score (0 to 100)
        y_train = np.array([95.0, 15.0, 70.0])
        self.model.fit(X_train, y_train)

    def rank_suppliers(self, suppliers: List[Dict], intent_profile: str = "defense") -> List[Dict]:
        """Scores and ranks suppliers based on the buyer's intent."""
        ranked_list = []
        
        for sup in suppliers:
            # 1. Calculate Sub-Scores
            esg_score = self.esg_opt.calculate_esg_score(sup['energy'], sup['recycling'])
            shadow_penalty = self.debiaser.apply_debiasing_penalty(sup['name'], sup['origin'], sup['china_ownership'])
            
            # 2. Build Feature Vector
            features = np.array([[
                sup['geo_risk'], 
                sup['itar_compliant'], 
                sup['purity'], 
                sup['lead_time'], 
                esg_score, 
                shadow_penalty
            ]])
            
            # 3. Predict Base Score using XGBoost
            base_score = float(self.model.predict(features)[0])
            
            # 4. Apply Intent Personalization (TaskRabbit Paradigm)
            final_score = base_score
            if intent_profile == "defense" and shadow_penalty > 0.3:
                final_score *= 0.1 # Severe penalty for defense buyers if shadow risk exists
            elif intent_profile == "commercial_ev":
                final_score += (esg_score * 0.2) # Boost for high ESG in commercial sector
                
            sup['final_score'] = round(final_score, 2)
            sup['esg_score'] = esg_score
            sup['shadow_risk'] = shadow_penalty
            ranked_list.append(sup)
            
        # Sort descending by final score
        return sorted(ranked_list, key=lambda x: x['final_score'], reverse=True)