import json
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.deps import get_current_active_user
from app import models
from app.schemas import EmailTestIn
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/email/test")
def send_test_email(
    body: EmailTestIn,
    _user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    # Prefer DB-stored settings (if present); fallback to .env settings.
    row = db.get(models.SmtpSettings, 1)
    host = (row.host if row else "") or settings.smtp_host
    port = (row.port if row else 0) or settings.smtp_port
    user = (row.user if row else "") or settings.smtp_user
    password = (row.password if row else "") or settings.smtp_password
    from_email = (row.from_email if row else "") or settings.smtp_from
    use_tls = (row.use_tls if row else None)
    if use_tls is None:
        use_tls = settings.smtp_use_tls

    if not host or not from_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chưa cấu hình SMTP (Settings → SMTP hoặc .env).",
        )
    msg = EmailMessage()
    msg["Subject"] = body.subject
    msg["From"] = from_email
    msg["To"] = body.to
    msg.set_content(body.body)
    try:
        if use_tls:
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port) as smtp:
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
    except OSError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return {"ok": True, "to": body.to}


@router.get("/zalo/webhook")
def zalo_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
) -> PlainTextResponse:
    if hub_mode == "subscribe" and hub_verify_token and settings.zalo_oa_verify_token:
        if hub_verify_token == settings.zalo_oa_verify_token and hub_challenge:
            return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify failed")


@router.post("/zalo/webhook")
async def zalo_webhook(request: Request) -> dict:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {"raw": (await request.body()).decode("utf-8", errors="replace")}
    return {"received": True, "event": payload}

