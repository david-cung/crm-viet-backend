from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_patch import run_schema_patches
from app.routers import (
    activities,
    auth,
    campaigns,
    chat,
    contacts,
    data_entry,
    deals,
    integrations,
    meta,
    notifications,
    reports,
    search,
    settings as settings_router,
    tasks,
    users,
)
from app.seed import ensure_company_defaults, ensure_default_admin, seed_if_empty
from app.security import decode_token
from app import models
from uuid import UUID
import json
from datetime import datetime, timezone
import uuid


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        run_schema_patches(conn)
    with SessionLocal() as db:
        seed_if_empty(db)
        ensure_default_admin(db)
        ensure_company_defaults(db)
    yield


app = FastAPI(title="CRM Việt API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://[::1]:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
for router in (
    contacts,
    deals,
    tasks,
    campaigns,
    activities,
    meta,
    reports,
    search,
    notifications,
    settings_router,
    integrations,
    users,
    chat,
    data_entry,
):
    app.include_router(router.router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}


def _ws_send(ws: WebSocket, payload: dict) -> None:
    # helper for consistent JSON
    return None


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    # auth via query token
    token = ws.query_params.get("token") or ""
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        user_id = UUID(str(sub))
    except Exception:  # noqa: BLE001
        await ws.close(code=1008)
        return

    await ws.accept()
    # Simple in-memory presence per-process (Phase 1). Redis pubsub can replace later.
    try:
        await ws.send_text(json.dumps({"type": "presence", "userId": str(user_id), "status": "online"}))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")
            if mtype == "typing_start":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "user_typing",
                            "conversationId": msg.get("conversationId"),
                            "userId": str(user_id),
                            "isTyping": True,
                        }
                    )
                )
            elif mtype == "typing_stop":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "user_typing",
                            "conversationId": msg.get("conversationId"),
                            "userId": str(user_id),
                            "isTyping": False,
                        }
                    )
                )
            elif mtype == "send_message":
                # For Phase 1 WS: persist via DB and echo new_message.
                conv_id = msg.get("conversationId")
                content = msg.get("content") or ""
                if not conv_id or not content:
                    continue
                from app.services.sanitize import sanitize_chat_text
                from app.services.chat_encryption import encrypt_message, decrypt_message
                from app.database import SessionLocal
                with SessionLocal() as db:
                    conv = db.get(models.Conversation, UUID(conv_id))
                    if not conv:
                        continue
                    member = (
                        db.query(models.ConversationMember)
                        .filter(models.ConversationMember.conversation_id == conv.id, models.ConversationMember.user_id == user_id)
                        .first()
                    )
                    if not member:
                        continue
                    plain = sanitize_chat_text(str(content))
                    if not plain:
                        continue
                    ct, iv, tag = encrypt_message(plain)
                    now = datetime.now(timezone.utc)
                    m = models.Message(
                        id=UUID(str(uuid.uuid4())),
                        conversation_id=conv.id,
                        sender_id=user_id,
                        content_encrypted=ct,
                        content_iv=iv,
                        content_tag=tag,
                        message_type="text",
                        reply_to_id=UUID(msg["replyToId"]) if msg.get("replyToId") else None,
                        reactions={},
                        is_deleted=False,
                        created_at=now,
                    )
                    db.add(m)
                    conv.updated_at = now
                    db.commit()
                    db.refresh(m)
                    await ws.send_text(
                        json.dumps(
                            {
                                "type": "new_message",
                                "message": {
                                    "id": str(m.id),
                                    "conversationId": str(m.conversation_id),
                                    "senderId": str(m.sender_id),
                                    "content": plain,
                                    "createdAt": m.created_at.isoformat(),
                                },
                            }
                        )
                    )
            elif mtype == "mark_read":
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "mark_read",
                            "conversationId": msg.get("conversationId"),
                            "messageId": msg.get("messageId"),
                            "userId": str(user_id),
                        }
                    )
                )
    except WebSocketDisconnect:
        return
    finally:
        try:
            await ws.send_text(json.dumps({"type": "presence", "userId": str(user_id), "status": "offline"}))
        except Exception:  # noqa: BLE001
            pass
