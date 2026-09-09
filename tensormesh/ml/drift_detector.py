import numpy as np

class DataDriftDetector:
    def __init__(self, z_score_threshold: float = 2.5):
        self.threshold = z_score_threshold

    def detect_volume_anomaly(self, historical_volumes: list, current_volume: float) -> dict:
        """
        Uses Z-Score statistical anomaly detection to flag sudden export bans 
        or massive dumping of minerals into the market.
        """
        if len(historical_volumes) < 5:
            return {"drift_detected": False, "reason": "Insufficient historical data"}
            
        mean_vol = np.mean(historical_volumes)
        std_vol = np.std(historical_volumes)
        
        if std_vol == 0:
            return {"drift_detected": False, "reason": "Zero variance in history"}
            
        z_score = abs((current_volume - mean_vol) / std_vol)
        
        is_anomaly = float(z_score) > self.threshold
        
        return {
            "drift_detected": is_anomaly,
            "z_score": round(z_score, 2),
            "severity": "HIGH" if z_score > 3.5 else "MEDIUM" if is_anomaly else "NORMAL",
            "message": f"Volume shifted by {round(z_score, 2)} standard deviations."
        }