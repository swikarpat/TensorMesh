class ShadowTradeDebiaser:
    def __init__(self):
        # High-risk transshipment hubs that artificially inflate their export numbers
        self.transshipment_hubs = ["Vietnam", "Malaysia", "Singapore", "Shadow Port A"]

    def apply_debiasing_penalty(self, supplier_name: str, reported_origin: str, ownership_china_percent: float) -> float:
        """
        Calculates a risk penalty (0.0 to 1.0) to debias the trade graph.
        1.0 = Maximum shadow trade risk.
        """
        penalty = 0.0
        
        if reported_origin in self.transshipment_hubs or supplier_name in self.transshipment_hubs:
            penalty += 0.4
            
        if ownership_china_percent > 25.0:
            penalty += 0.5
            
        return min(1.0, penalty)