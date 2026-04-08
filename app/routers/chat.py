from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_active_user
from app.services.chat_encryption import decrypt_message, encrypt_message
from app.services.sanitize import sanitize_chat_text
from app.services.s3 import generate_presigned_url, upload_file

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_active_user)])


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
    name: str
    avatar_url: str = Field(serialization_alias="avatarUrl")
    unread_count: int = Field(default=0, serialization_alias="unreadCount")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class CreateConversationIn(BaseModel):
    type: str = "direct"  # direct | group
    name: str = ""
    avatar_url: str = Field(default="", alias="avatarUrl")
    member_ids: list[str] = Field(default_factory=list, alias="memberIds")


class MemberOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    user_id: str = Field(serialization_alias="userId")
    role: str
    joined_at: datetime = Field(serialization_alias="joinedAt")
    last_read_at: datetime | None = Field(default=None, serialization_alias="lastReadAt")
    is_muted: bool = Field(serialization_alias="isMuted")


class MessageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    conversation_id: str = Field(serialization_alias="conversationId")
    sender_id: str = Field(serialization_alias="senderId")
    content: str
    message_type: str = Field(serialization_alias="messageType")
    file_id: str | None = Field(default=None, serialization_alias="fileId")
    reply_to_id: str | None = Field(default=None, serialization_alias="replyToId")
    reactions: dict = Field(default_factory=dict)
    is_deleted: bool = Field(serialization_alias="isDeleted")
    created_at: datetime = Field(serialization_alias="createdAt")


class SendMessageIn(BaseModel):
    content: str
    reply_to_id: str | None = Field(default=None, alias="replyToId")


class ReactIn(BaseModel):
    emoji: str


class MarkReadIn(BaseModel):
    message_id: str = Field(alias="messageId")


class UploadOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    file_id: str = Field(serialization_alias="fileId")
    s3_key: str = Field(serialization_alias="s3Key")


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)) -> list[ConversationOut]:
    # Note: unread_count will be computed as messages after member.last_read_at
    mems = db.query(models.ConversationMember).filter(models.ConversationMember.user_id == user.id).all()
    conv_ids = [m.conversation_id for m in mems]
    if not conv_ids:
        return []
    convs = db.query(models.Conversation).filter(models.Conversation.id.in_(conv_ids)).order_by(models.Conversation.updated_at.desc()).all()
    last_read_by_conv = {m.conversation_id: m.last_read_at for m in mems}
    out: list[ConversationOut] = []
    for c in convs:
        lr = last_read_by_conv.get(c.id)
        q = db.query(models.Message).filter(models.Message.conversation_id == c.id, models.Message.is_deleted.is_(False))
        if lr:
            q = q.filter(models.Message.created_at > lr)
        unread = q.count()
        out.append(
            ConversationOut(
                id=str(c.id),
                type=c.type,
                name=c.name,
                avatar_url=c.avatar_url,
                unread_count=unread,
                updated_at=c.updated_at,
            )
        )
    return out


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> ConversationOut:
    c = models.Conversation(
        type=body.type,
        name=body.name or "",
        avatar_url=body.avatar_url or "",
        created_by=user.id,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(c)
    db.flush()

    member_ids: list[UUID] = []
    for mid in body.member_ids:
        try:
            member_ids.append(UUID(mid))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid memberIds") from None
    # Ensure creator is a member
    if user.id not in member_ids:
        member_ids.append(user.id)

    for uid in member_ids:
        role = "admin" if uid == user.id else "member"
        db.add(
            models.ConversationMember(
                conversation_id=c.id,
                user_id=uid,
                role=role,
                joined_at=_now(),
                last_read_at=None,
                is_muted=False,
            )
        )
    db.commit()
    db.refresh(c)
    return ConversationOut(id=str(c.id), type=c.type, name=c.name, avatar_url=c.avatar_url, unread_count=0, updated_at=c.updated_at)


@router.get("/conversations/{conversation_id}", response_model=dict)
def get_conversation_detail(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> dict:
    c = db.get(models.Conversation, conversation_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    is_member = (
        db.query(models.ConversationMember)
        .filter(models.ConversationMember.conversation_id == c.id, models.ConversationMember.user_id == user.id)
        .first()
        is not None
    )
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    mems = db.query(models.ConversationMember).filter(models.ConversationMember.conversation_id == c.id).all()
    return {
        "id": str(c.id),
        "type": c.type,
        "name": c.name,
        "avatarUrl": c.avatar_url,
        "members": [
            MemberOut(
                user_id=str(m.user_id),
                role=m.role,
                joined_at=m.joined_at,
                last_read_at=m.last_read_at,
                is_muted=m.is_muted,
            ).model_dump(by_alias=True)
            for m in mems
        ],
    }


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: UUID,
    before: UUID | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> list[MessageOut]:
    mem = (
        db.query(models.ConversationMember)
        .filter(models.ConversationMember.conversation_id == conversation_id, models.ConversationMember.user_id == user.id)
        .first()
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    q = db.query(models.Message).filter(models.Message.conversation_id == conversation_id).order_by(models.Message.created_at.desc())
    if before:
        b = db.get(models.Message, before)
        if b:
            q = q.filter(models.Message.created_at < b.created_at)
    rows = q.limit(limit).all()
    out: list[MessageOut] = []
    for m in rows:
        content = ""
        if not m.is_deleted and m.content_encrypted and m.content_iv and m.content_tag:
            try:
                content = decrypt_message(m.content_encrypted, m.content_iv, m.content_tag)
            except Exception:  # noqa: BLE001
                content = ""
        out.append(
            MessageOut(
                id=str(m.id),
                conversation_id=str(m.conversation_id),
                sender_id=str(m.sender_id),
                content=content,
                message_type=m.message_type,
                file_id=str(m.file_id) if m.file_id else None,
                reply_to_id=str(m.reply_to_id) if m.reply_to_id else None,
                reactions=m.reactions or {},
                is_deleted=m.is_deleted,
                created_at=m.created_at,
            )
        )
    return out


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: UUID,
    body: SendMessageIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> MessageOut:
    mem = (
        db.query(models.ConversationMember)
        .filter(models.ConversationMember.conversation_id == conversation_id, models.ConversationMember.user_id == user.id)
        .first()
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    plain = sanitize_chat_text(body.content)
    if not plain:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty message")
    ct, iv, tag = encrypt_message(plain)
    mid = uuid.uuid4()
    m = models.Message(
        id=mid,
        conversation_id=conversation_id,
        sender_id=user.id,
        content_encrypted=ct,
        content_iv=iv,
        content_tag=tag,
        message_type="text",
        file_id=None,
        reply_to_id=UUID(body.reply_to_id) if body.reply_to_id else None,
        reactions={},
        is_deleted=False,
        created_at=_now(),
    )
    db.add(m)
    conv = db.get(models.Conversation, conversation_id)
    if conv:
        conv.updated_at = _now()
    db.commit()
    db.refresh(m)
    return MessageOut(
        id=str(m.id),
        conversation_id=str(m.conversation_id),
        sender_id=str(m.sender_id),
        content=plain,
        message_type=m.message_type,
        file_id=None,
        reply_to_id=str(m.reply_to_id) if m.reply_to_id else None,
        reactions={},
        is_deleted=False,
        created_at=m.created_at,
    )


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> None:
    m = db.get(models.Message, message_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if m.sender_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete your message")
    m.is_deleted = True
    m.deleted_at = _now()
    db.commit()


@router.post("/messages/{message_id}/react", response_model=MessageOut)
def react_message(
    message_id: UUID,
    body: ReactIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> MessageOut:
    m = db.get(models.Message, message_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    rx = dict(m.reactions or {})
    users = set(rx.get(body.emoji, []))
    uid = str(user.id)
    if uid in users:
        users.remove(uid)
    else:
        users.add(uid)
    rx[body.emoji] = sorted(users)
    m.reactions = rx
    db.commit()
    db.refresh(m)
    content = ""
    if not m.is_deleted and m.content_encrypted and m.content_iv and m.content_tag:
        try:
            content = decrypt_message(m.content_encrypted, m.content_iv, m.content_tag)
        except Exception:  # noqa: BLE001
            content = ""
    return MessageOut(
        id=str(m.id),
        conversation_id=str(m.conversation_id),
        sender_id=str(m.sender_id),
        content=content,
        message_type=m.message_type,
        file_id=str(m.file_id) if m.file_id else None,
        reply_to_id=str(m.reply_to_id) if m.reply_to_id else None,
        reactions=m.reactions or {},
        is_deleted=m.is_deleted,
        created_at=m.created_at,
    )


@router.post("/messages/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> None:
    m = db.get(models.Message, message_id)
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    mem = (
        db.query(models.ConversationMember)
        .filter(models.ConversationMember.conversation_id == m.conversation_id, models.ConversationMember.user_id == user.id)
        .first()
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    mem.last_read_at = _now()
    rr = db.get(models.MessageReadReceipt, {"message_id": m.id, "user_id": user.id})
    if not rr:
        rr = models.MessageReadReceipt(message_id=m.id, user_id=user.id, read_at=_now())
        db.add(rr)
    db.commit()


@router.post("/files/upload", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_chat_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> UploadOut:
    raw = await file.read()
    fid = uuid.uuid4()
    s3_key = f"chat/{user.id}/{fid}/{file.filename}"
    upload_file(file_bytes=raw, s3_key=s3_key, content_type=file.content_type)
    mf = models.MessageFile(
        id=fid,
        uploader_id=user.id,
        original_name=file.filename or "",
        file_size=len(raw),
        mime_type=file.content_type or "",
        s3_key=s3_key,
        created_at=_now(),
    )
    db.add(mf)
    db.commit()
    return UploadOut(file_id=str(fid), s3_key=s3_key)


@router.get("/files/{file_id}/url")
def get_file_url(
    file_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_active_user),
) -> dict:
    mf = db.get(models.MessageFile, file_id)
    if not mf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    pres = generate_presigned_url(s3_key=mf.s3_key, expires=900)
    return {"url": pres.url, "expiresIn": pres.expires_in}


@router.get("/unread", response_model=dict)
def unread_total(db: Session = Depends(get_db), user: models.User = Depends(get_current_active_user)) -> dict:
    mems = db.query(models.ConversationMember).filter(models.ConversationMember.user_id == user.id).all()
    total = 0
    for m in mems:
        q = db.query(models.Message).filter(models.Message.conversation_id == m.conversation_id, models.Message.is_deleted.is_(False))
        if m.last_read_at:
            q = q.filter(models.Message.created_at > m.last_read_at)
        total += q.count()
    return {"total": total}

