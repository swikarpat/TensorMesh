class ESGOptimizer:
    def __init__(self):
        # Base carbon intensity (kg CO2 per kg of Rare Earth)
        self.energy_profiles = {
            "coal": 25.0,
            "grid_mixed": 12.5,
            "solar_hydro": 4.0
        }

    def calculate_esg_score(self, energy_source: str, recycling_percent: float) -> float:
        """
        Calculates an ESG score from 0 to 100.
        Higher is better (greener).
        """
        base_emissions = self.energy_profiles.get(energy_source.lower(), 20.0)
        
        # Recycling reduces the carbon footprint penalty
        adjusted_emissions = base_emissions * (1 - (recycling_percent / 100.0))
        
        # Normalize to a 0-100 score (assuming 30.0 is the worst possible emissions)
        score = max(0.0, 100.0 - (adjusted_emissions / 30.0 * 100.0))
        return round(score, 2)