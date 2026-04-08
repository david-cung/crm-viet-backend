import json
import smtplib
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.deps import get_current_active_user
from app import models
from app.schemas import EmailTestIn

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/email/test")
def send_test_email(body: EmailTestIn, _user: models.User = Depends(get_current_active_user)) -> dict:
    if not settings.smtp_host or not settings.smtp_from:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chưa cấu hình SMTP (smtp_host, smtp_from trong .env).",
        )
    msg = EmailMessage()
    msg["Subject"] = body.subject
    msg["From"] = settings.smtp_from
    msg["To"] = body.to
    msg.set_content(body.body)
    try:
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
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

