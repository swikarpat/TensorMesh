from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "TensorMesh"
    VERSION: str = "1.0.0"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    ROCKSDB_PATH: Path = DATA_DIR / "rocksdb"
    KEY_PATH: Path = DATA_DIR / "vault.key"
    
    # Hardware Routing Thresholds
    VRAM_WARNING_THRESHOLD_PERCENT: float = 85.0
    
    # Model Routing
    HEAVY_MODEL: str = "claude-3-5-sonnet-20240620"
    LOCAL_SLM: str = "llama3.1:8b"

    class Config:
        env_file = ".env"

# Ensure data directories exist
settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)