from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "SensorHub"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    RAW_DIR: Path = STORAGE_DIR / "raw"
    PROCESSED_DIR: Path = STORAGE_DIR / "processed"
    
    # Database
    DB_DIR: Path = BASE_DIR / "database"
    USE_TEST_DB: bool = False
    
    @property
    def SQLITE_URL(self) -> str:
        db_name = "test.db" if self.USE_TEST_DB else "sensorhub.db"
        return f"sqlite:///{self.DB_DIR}/{db_name}"
    
    class Config:
        case_sensitive = True

settings = Settings()
