from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "ChainSight API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
    DEFILLAMA_BASE_URL: str = "https://api.llama.fi"
    ETHERSCAN_BASE_URL: str = "https://api.etherscan.io/v2/api"
    FEAR_GREED_URL: str = "https://api.alternative.me/fng/"

    ETHERSCAN_API_KEY: str = ""
    GOLDRUSH_API_KEY: str = ""

    CACHE_TTL: int = 60


settings = Settings()
