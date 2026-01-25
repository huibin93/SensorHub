"""
应用配置模块。

本模块定义了应用的所有配置类，从 config.json 文件加载配置。
包括应用信息、服务器设置、CORS 设置和数据库配置。
"""
from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from pathlib import Path
import json
from typing import Any, Dict, Tuple, Type


class AppConfig(BaseModel):
    """应用基本信息配置。"""
    name: str
    version: str
    debug: bool


class ServerConfig(BaseModel):
    """服务器配置。"""
    host: str
    port: int
    reload: bool


class CorsConfig(BaseModel):
    """跨域资源共享 (CORS) 配置。"""
    allowed_origins: list[str]


class DatabaseConfig(BaseModel):
    """数据库配置。"""
    directory: str
    use_test_db: bool
    echo: bool


class StorageConfig(BaseModel):
    """存储配置。"""
    zip_pp: str


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    """
    从 JSON 文件加载配置的设置源。

    读取 backend/config.json 文件并解析为配置字典。
    """

    def get_field_value(self, field: Any, field_name: str) -> Tuple[Any, str, bool]:
        """获取字段值（继承自父类）。"""
        return super().get_field_value(field, field_name)

    def __call__(self) -> Dict[str, Any]:
        """
        加载并返回配置字典。

        Returns:
            从 config.json 解析的配置字典，文件不存在时返回空字典。
        """
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "config.json"

        try:
            with open(config_path, encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            from app.core.logger import logger
            logger.warning(f"{config_path} not found.")
            return {}


class Settings(BaseSettings):
    """
    应用全局设置。

    整合所有配置子模块，并提供计算属性用于获取各种路径。
    """
    app: AppConfig
    server: ServerConfig
    cors: CorsConfig
    database: DatabaseConfig
    storage: StorageConfig

    # 固定/计算字段
    API_V1_STR: str = "/api"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    @property
    def STORAGE_DIR(self) -> Path:
        """存储根目录路径。"""
        return self.BASE_DIR / "storage"

    @property
    def RAW_DIR(self) -> Path:
        """原始文件存储目录路径。"""
        return self.STORAGE_DIR / "raw"

    @property
    def PROCESSED_DIR(self) -> Path:
        """处理后文件存储目录路径。"""
        return self.STORAGE_DIR / "processed"

    @property
    def DB_DIR(self) -> Path:
        """数据库文件目录路径。"""
        path = Path(self.database.directory)
        if path.is_absolute():
            return path
        return self.BASE_DIR / path

    @property
    def SQLITE_URL(self) -> str:
        """SQLite 数据库连接 URL。"""
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        filename = "test.db" if self.database.use_test_db else "sensorhub.db"
        return f"sqlite:///{self.DB_DIR}/{filename}"

    @property
    def PROJECT_NAME(self) -> str:
        """项目名称。"""
        return self.app.name

    @property
    def USE_TEST_DB(self) -> bool:
        """是否使用测试数据库。"""
        return self.database.use_test_db

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """自定义配置源，仅使用 JSON 文件。"""
        return (JsonConfigSettingsSource(settings_cls),)


settings = Settings()
