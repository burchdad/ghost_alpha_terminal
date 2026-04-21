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
    llm_provider: str = "openai-compatible"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    copilot_llm_enabled: bool = False
    copilot_llm_rollout_pct: int = 0
    copilot_openai_enabled: bool = False
    copilot_openai_rollout_pct: int = 0

    # ---------------------------------------------------------------------------
    # External market data providers
    # ---------------------------------------------------------------------------
    massive_api_key: str = ""
    finnhub_api_key: str = ""
    fmp_api_key: str = ""  # Financial Modeling Prep
    dynamic_universe_enabled: bool = True
    dynamic_universe_sources: str = "finnhub,fmp,massive,static"
    dynamic_universe_max_symbols: int = 180
    dynamic_universe_refresh_seconds: int = 3600

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
    # Charles Schwab OAuth credentials
    # ---------------------------------------------------------------------------
    schwab_client_id: str = ""
    schwab_client_secret: str = ""
    schwab_redirect_uri: str = ""
    schwab_authorize_url: str = "https://api.schwab.com/v1/oauth/authorize"
    schwab_token_url: str = "https://api.schwab.com/v1/oauth/token"

    # ---------------------------------------------------------------------------
    # Auth/session settings
    # ---------------------------------------------------------------------------
    auth_session_secret: str = ""
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_persistent: bool = True
    frontend_base_url: str = "http://localhost:3000"
    auth_access_ttl_minutes: int = 30
    auth_refresh_ttl_days: int = 14
    risk_new_ip_prefix_length: int = 24
    login_failure_window_minutes: int = 15
    login_progressive_delay_after_failures: int = 5
    login_progressive_delay_seconds: int = 1
    login_lock_after_failures: int = 10
    login_lock_minutes: int = 15

    # ---------------------------------------------------------------------------
    # 2FA / OTP settings
    # ---------------------------------------------------------------------------
    otp_code_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_lockout_minutes: int = 10
    trusted_device_days: int = 30
    high_trust_session_minutes: int = 30
    webauthn_challenge_ttl_seconds: int = 300
    webauthn_rp_id: str = "localhost"
    webauthn_rp_origin: str = "http://localhost:3000"
    webauthn_assertion_window_minutes: int = 10
    withdrawal_step_up_max_age_minutes: int = 10
    withdrawal_first_cooldown_minutes: int = 20
    withdrawal_new_destination_cooldown_minutes: int = 30
    withdrawal_anomaly_amount_multiplier: float = 3.0
    withdrawal_anomaly_amount_absolute: float = 25000
    withdrawal_anomaly_timing_hour_delta: int = 6
    withdrawal_hold_on_anomaly: bool = True
    withdrawal_approval_ttl_minutes: int = 30
    fraud_agent_escalate_score: int = 60
    fraud_agent_block_score: int = 85
    password_reset_ttl_minutes: int = 30
    password_reset_max_attempts: int = 5
    password_reset_request_window_minutes: int = 15
    password_reset_request_max_per_ip: int = 10
    password_reset_request_max_per_email: int = 5
    password_reset_submit_window_minutes: int = 15
    password_reset_submit_max_per_ip: int = 20
    password_reset_captcha_after_attempts: int = 3
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    twofa_totp_issuer: str = "Ghost Alpha Terminal"

    # Twilio Verify (preferred — no from-number required)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_service_sid: str = ""  # VAxxxxxxxxx — Verify Service SID
    # Legacy Twilio Messages API (fallback if Verify SID not set)
    twilio_phone_number: str = ""

    # Discord webhook alerts
    discord_alerts_enabled: bool = False
    discord_webhook_url: str = ""
    discord_username: str = "Ghost Alpha Ops"
    discord_timeout_seconds: float = 5.0
    discord_min_interval_seconds: int = 600

    # Discord inbound event webhooks (Developer Portal -> Webhooks -> Endpoint URL)
    discord_inbound_enabled: bool = False
    discord_public_key: str = ""
    discord_inbound_max_body_kb: int = 64

    # SendGrid (preferred when API key is set)
    sendgrid_api_key: str = ""
    sendgrid_from: str = ""

    # SMTP email (fallback when SendGrid is not configured)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_starttls: bool = True
    smtp_use_ssl: bool = False

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
    # Tradier API credentials (platform key mode)
    # ---------------------------------------------------------------------------
    tradier_sandbox_api_key: str = ""
    tradier_sandbox_account_number: str = ""
    tradier_live_api_key: str = ""
    tradier_live_account_number: str = ""

    # Legacy single-credential vars (kept for backward compatibility)
    tradier_api_key: str = ""
    tradier_account_number: str = ""
    tradier_sandbox: bool = True
    tradier_live_trading_enabled: bool = True
    tradier_base_url: str = ""

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

    # ---------------------------------------------------------------------------
    # API guardrails (rate limiting + scoped API keys)
    # ---------------------------------------------------------------------------
    api_rate_limit_window_seconds: int = 60
    api_rate_limit_anon: int = 90
    api_rate_limit_session: int = 240
    api_rate_limit_readonly_key: int = 360
    api_rate_limit_trading_key: int = 240
    api_key_readonly: str = ""
    api_key_trading: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def tradier_effective_api_key(self) -> str:
        if self.tradier_sandbox:
            return self.tradier_sandbox_api_key or self.tradier_api_key
        return self.tradier_live_api_key or self.tradier_api_key

    @property
    def tradier_effective_account_number(self) -> str:
        if self.tradier_sandbox:
            return self.tradier_sandbox_account_number or self.tradier_account_number
        return self.tradier_live_account_number or self.tradier_account_number

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

    @field_validator("smtp_port", mode="before")
    @classmethod
    def parse_smtp_port(cls, value):
        """Accept integer SMTP ports and provider doc strings like '25,587,465'."""
        if isinstance(value, int):
            return value
        if value is None:
            return 587

        raw = str(value).strip()
        if not raw:
            return 587

        candidates: list[int] = []
        for token in raw.split(","):
            token = token.strip()
            if token.isdigit():
                candidates.append(int(token))

        if not candidates:
            raise ValueError("smtp_port must be an integer SMTP port such as 587")

        # Prefer STARTTLS port when multiple ports are provided.
        if 587 in candidates:
            return 587
        if 465 in candidates:
            return 465
        return candidates[0]

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

            if self.effective_copilot_llm_enabled and not self.effective_llm_api_key:
                errors.append("LLM_API_KEY or OPENAI_API_KEY must be set when copilot LLM routing is enabled")

            if self.effective_copilot_llm_rollout_pct < 0 or self.effective_copilot_llm_rollout_pct > 100:
                errors.append("Copilot LLM rollout percentage must be between 0 and 100")

            if self.discord_inbound_enabled and not self.discord_public_key:
                errors.append("DISCORD_PUBLIC_KEY must be set when DISCORD_INBOUND_ENABLED is true")
        
        if errors:
            raise ValueError(
                f"Production configuration validation failed:\n" + 
                "\n".join(f"  - {e}" for e in errors)
            )

    @property
    def effective_llm_api_key(self) -> str:
        return self.llm_api_key or self.openai_api_key

    @property
    def effective_llm_model(self) -> str:
        return self.llm_model or self.openai_model

    @property
    def effective_llm_base_url(self) -> str | None:
        value = self.llm_base_url.strip()
        return value or None

    @property
    def effective_copilot_llm_enabled(self) -> bool:
        return bool(self.copilot_llm_enabled or self.copilot_openai_enabled)

    @property
    def effective_copilot_llm_rollout_pct(self) -> int:
        return self.copilot_llm_rollout_pct if self.copilot_llm_rollout_pct > 0 else self.copilot_openai_rollout_pct


settings = Settings()

# Validate production config on import
if settings.app_env != "dev":
    settings.validate_production_config()
