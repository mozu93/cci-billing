# app/services/email_service.py
import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from app.utils.app_config import get_config


def get_smtp_config() -> dict:
    return get_config().get("smtp", {})


def _build_message(smtp_config: dict, to_addr: str, subject: str,
                   body: str, pdf_path: str | None = None,
                   is_test: bool = False) -> MIMEMultipart:
    msg = MIMEMultipart()
    from_addr = smtp_config.get("from_addr", "")
    from_name = smtp_config.get("from_name", "")
    msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
    msg["To"] = to_addr
    msg["Subject"] = Header(
        f"【テスト】{subject}" if is_test else subject, "utf-8"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part["Content-Disposition"] = (
            f'attachment; filename="{os.path.basename(pdf_path)}"'
        )
        msg.attach(part)
    return msg


def send_email(to_addr: str, subject: str, body: str,
               pdf_path: str | None = None) -> None:
    config = get_smtp_config()
    msg = _build_message(config, to_addr, subject, body, pdf_path)
    _send(config, to_addr, msg)


def send_test_email(subject: str, body: str,
                    pdf_path: str | None = None) -> None:
    config = get_smtp_config()
    test_addr = config.get("test_addr", "")
    if not test_addr:
        raise ValueError("テスト送信先メールアドレスが設定されていません。")
    msg = _build_message(config, test_addr, subject, body, pdf_path, is_test=True)
    _send(config, test_addr, msg)


def _send(config: dict, to_addr: str, msg: MIMEMultipart) -> None:
    host = config.get("host", "")
    port = int(config.get("port", 587))
    user = config.get("user", "")
    password = config.get("password", "")
    use_tls = config.get("use_tls", True)

    if not host:
        raise ValueError("SMTPサーバーが設定されていません。")

    if use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.ehlo()
            s.starttls(context=context)
            if user:
                s.login(user, password)
            s.sendmail(msg["From"], [to_addr], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            if user:
                s.login(user, password)
            s.sendmail(msg["From"], [to_addr], msg.as_string())


def build_issuance_email(issuance, company_name: str,
                          template_subject: str = "",
                          template_body: str = "") -> tuple[str, str]:
    doc_label = "請求書" if issuance.doc_type == "invoice" else "領収書"
    subject = template_subject or f"【{company_name}】{doc_label}をお送りします"
    recipient = (issuance.recipient_organization or issuance.recipient_name or "")
    body = template_body or (
        f"{recipient} 様\n\n"
        f"お世話になっております。{company_name}でございます。\n\n"
        f"{doc_label}（{issuance.doc_number}）をお送りします。\n"
        f"金額：¥{int(issuance.amount):,}（税込）\n\n"
        "ご確認のほどよろしくお願いいたします。\n\n"
        f"{company_name}"
    )
    return subject, body
