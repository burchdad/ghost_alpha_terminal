from pydantic import field_validator
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
    # Auth/session settings
    # ---------------------------------------------------------------------------
    auth_session_secret: str = ""
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    frontend_base_url: str = "http://localhost:3000"

    # ---------------------------------------------------------------------------
    # Coinbase Advanced Trade API credentials
    # ---------------------------------------------------------------------------
    coinbase_api_key_name: str = ""
    coinbase_api_private_key: str = ""
    coinbase_live_trading_enabled: bool = True
    coinbase_trade_products: str = "BTC-USD,ETH-USD,SOL-USD,LINK-USD,AVAX-USD,LTC-USD,ADA-USD,XRP-USD,DOGE-USD,BCH-USD"
    coinbase_ws_enabled: bool = True
    coinbase_ws_products: str = "BTC-USD,ETH-USD,SOL-USD,LINK-USD,AVAX-USD,LTC-USD,ADA-USD,XRP-USD,DOGE-USD,BCH-USD"
    coinbase_ws_url: str = "wss://advanced-trade-ws.coinbase.com"

    # ---------------------------------------------------------------------------
    # High-risk sprint mode — opt-in low-priced equity universe for paper sprints
    # ---------------------------------------------------------------------------
    high_risk_sprint_mode_enabled: bool = False
    high_risk_sprint_auto_enabled: bool = True
    high_risk_sprint_auto_trigger_pressure: float = 1.75
    high_risk_sprint_symbols: str = "SOUN,ACHR,JOBY,OPEN,LCID,PLUG,DNA,SOFI,RKLB,HUT,RIOT,IREN"
    high_risk_sprint_max_price: float = 15.0
    high_risk_sprint_min_dollar_volume: float = 4_000_000
    high_risk_sprint_max_spread_proxy: float = 0.14

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

    @field_validator("auth_cookie_secure", mode="before")
    @classmethod
    def parse_auth_cookie_secure(cls, value):
        """Accept strict booleans and common descriptive env strings."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False

        raw = str(value).strip().lower()
        first_token = raw.split()[0] if raw else ""

        if first_token in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if first_token in {"0", "false", "f", "no", "n", "off"}:
            return False

        raise ValueError(
            "auth_cookie_secure must be a boolean value (true/false, 1/0, yes/no)."
        )

    def validate_production_config(self) -> None:
        """Validate that critical environment variables are set for production."""
        errors = []
        
        if self.app_env != "dev":
            # Production requires explicit DATABASE_URL and not just SQLite default
            if self.database_url.startswith("sqlite://"):
                errors.append("DATABASE_URL must be set to a production database (not SQLite)")
            
            if not self.auth_session_secret or len(self.auth_session_secret) < 32:
                errors.append("AUTH_SESSION_SECRET must be set and at least 32 characters")
            
            if not self.alpaca_connect_client_id:
                errors.append("ALPACA_CONNECT_CLIENT_ID must be set")
            
            if not self.alpaca_connect_client_secret:
                errors.append("ALPACA_CONNECT_CLIENT_SECRET must be set")
            
            if not self.alpaca_connect_redirect_uri:
                errors.append("ALPACA_CONNECT_REDIRECT_URI must be set")
        
        if errors:
            raise ValueError(
                f"Production configuration validation failed:\n" + 
                "\n".join(f"  - {e}" for e in errors)
            )


settings = Settings()

# Validate production config on import
if settings.app_env != "dev":
    settings.validate_production_config()
