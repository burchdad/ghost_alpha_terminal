from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GHOST ALPHA TERMINAL API"
    app_version: str = "0.1.0"
    app_env: str = "dev"

    # ---------------------------------------------------------------------------
    # Server
    # ---------------------------------------------------------------------------
    port: int = 8000                 # Railway injects $PORT automatically

    # ---------------------------------------------------------------------------
    # CORS — comma-separated list of allowed origins.
    # Set ALLOWED_ORIGINS=https://your-frontend.up.railway.app in production.
    # Defaults to * so local dev works without config.
    # ---------------------------------------------------------------------------
    allowed_origins: str = "*"

    # ---------------------------------------------------------------------------
    # Database — Railway auto-provisions Postgres and sets DATABASE_URL.
    # Falls back to local SQLite for development.
    # ---------------------------------------------------------------------------
    database_url: str = "sqlite:///./ghost_alpha_terminal.db"

    # ---------------------------------------------------------------------------
    # Redis / Celery (optional — only needed if queue tasks are active)
    # ---------------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---------------------------------------------------------------------------
    # AI / ML
    # ---------------------------------------------------------------------------
    kronos_model_id: str = "NeoQuasar/Kronos-tiny"
    use_mock_data: bool = False

    # ---------------------------------------------------------------------------
    # Alpaca credentials — set via Railway environment variables, never committed
    # ---------------------------------------------------------------------------
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True        # True = paper endpoint, False = live capital

    # ---------------------------------------------------------------------------
    # Alpaca Connect (OAuth app) credentials
    # ---------------------------------------------------------------------------
    alpaca_connect_client_id: str = ""
    alpaca_connect_client_secret: str = ""
    alpaca_connect_redirect_uri: str = ""
    alpaca_connect_authorize_url: str = "https://app.alpaca.markets/oauth/authorize"
    alpaca_connect_token_url: str = "https://api.alpaca.markets/oauth/token"

    # ---------------------------------------------------------------------------
    # Coinbase Advanced Trade API credentials
    # ---------------------------------------------------------------------------
    coinbase_api_key_name: str = ""
    coinbase_api_private_key: str = ""
    coinbase_live_trading_enabled: bool = True
    coinbase_trade_products: str = "BTC-USD,ETH-USD,SOL-USD"
    coinbase_ws_enabled: bool = True
    coinbase_ws_products: str = "BTC-USD,ETH-USD,SOL-USD"
    coinbase_ws_url: str = "wss://advanced-trade-ws.coinbase.com"

    # ---------------------------------------------------------------------------
    # Misc
    # ---------------------------------------------------------------------------
    request_id_max_entries: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parse ALLOWED_ORIGINS into a list for FastAPI's CORSMiddleware."""
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
