import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def send_verification_email(to_email: str, code: str, name: str) -> None:
    subject = "[RE-ACT 리액트봇] 부원 인증 코드"
    body = (
        f"{name}님, 안녕하세요.\n\n"
        f"RE-ACT 디스코드 부원 인증 코드는 [{code}] 입니다.\n"
        f"디스코드에서 /인증확인 코드:{code} 를 입력해주세요.\n\n"
        f"{settings.verification_code_ttl_minutes}분 이내에 입력하지 않으면 코드가 만료됩니다."
    )

    if not settings.smtp_configured:
        print(f"[mailer:mock] to={to_email} subject={subject!r}\n{body}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from, [to_email], msg.as_string())
