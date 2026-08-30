from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Discord
    discord_token: str = ""
    discord_guild_id: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""

    # 웹 / 세션
    web_base_url: str = "http://localhost:8000"
    port: int = 8000
    cookie_secret: str = "change-me"
    session_max_age_seconds: int = 60 * 60 * 12

    # 내부 서비스 간 인증 (discord-bot <-> backend)
    internal_api_key: str = "change-me"

    # 부트스트랩 관리자 (콤마 구분 discord user id 목록)
    super_admin_discord_ids: str = ""

    # DB
    database_url: str = "sqlite:///./app.db"

    # SMTP (학교 이메일 인증코드 발송)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "RE-ACT 리액트봇 <no-reply@example.com>"
    smtp_use_tls: bool = True

    verification_code_ttl_minutes: int = 10
    verification_max_attempts: int = 5

    # GitHub 웹훅 (PR/이슈 알림)
    github_webhook_secret: str = ""

    @property
    def super_admin_ids(self) -> list[str]:
        return [x.strip() for x in self.super_admin_discord_ids.split(",") if x.strip()]

    @property
    def discord_configured(self) -> bool:
        return bool(self.discord_token and self.discord_guild_id)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)


settings = Settings()
