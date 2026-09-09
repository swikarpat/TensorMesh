import psutil
from tensormesh.config.settings import settings

class HardwareRouter:
    def __init__(self):
        self.warning_threshold = settings.VRAM_WARNING_THRESHOLD_PERCENT

    def get_system_memory_usage(self) -> float:
        """Returns the percentage of unified memory currently in use."""
        memory_info = psutil.virtual_memory()
        return memory_info.percent

    def route_model(self, ast_complexity_score: int) -> str:
        """
        Dynamically routes to Heavy Cloud LLM or Local SLM based on 
        task complexity and current MacBook Unified Memory pressure.
        """
        current_ram_usage = self.get_system_memory_usage()
        
        # If RAM is critically high, force routing to cloud to prevent OOM crash
        if current_ram_usage > self.warning_threshold:
            print(f"[HardwareRouter] WARNING: Unified Memory at {current_ram_usage}%. Forcing Cloud LLM.")
            return settings.HEAVY_MODEL
            
        # Normal routing based on AST Complexity
        if ast_complexity_score >= 5:
            return settings.HEAVY_MODEL
        else:
            return settings.LOCAL_SLM