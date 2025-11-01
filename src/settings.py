import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8080
    FTP_PORT: int = 2121

    TARGET_DIR: str = None

    CHECK_MUST_EXISTS: bool = False

    model_config = SettingsConfigDict(env_file=os.path.normpath(os.path.join(__file__, "../../.env.local")))

settings = Settings()
