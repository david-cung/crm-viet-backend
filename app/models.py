import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(String(512), default="")
    birthday: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    zalo: Mapped[str] = mapped_column(String(128), default="")
    facebook: Mapped[str] = mapped_column(String(255), default="")
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, insert_default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    source: Mapped[str] = mapped_column(String(128), default="")
    assigned_to: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())

    deals: Mapped[list["Deal"]] = relationship("Deal", back_populates="contact")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="staff")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False)
    assigned_to: Mapped[str] = mapped_column(String(255), default="")
    stage: Mapped[str] = mapped_column(String(64), nullable=False, default="new_lead")
    probability: Mapped[int] = mapped_column(nullable=False, default=0)
    close_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())

    contact: Mapped["Contact"] = relationship("Contact", back_populates="deals")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    assigned_to: Mapped[str] = mapped_column(String(255), default="")
    due_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    linked_contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    linked_deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id"), nullable=True
    )

    linked_contact: Mapped[Optional["Contact"]] = relationship("Contact", foreign_keys=[linked_contact_id])
    linked_deal: Mapped[Optional["Deal"]] = relationship("Deal", foreign_keys=[linked_deal_id])


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(128), default="")
    budget: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    spent: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    start_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    leads_generated: Mapped[int] = mapped_column(nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(nullable=False, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    time: Mapped[str] = mapped_column(String(128), nullable=False)
    user: Mapped[str] = mapped_column(String(255), default="")
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    contact: Mapped[Optional["Contact"]] = relationship("Contact", foreign_keys=[contact_id])
    deal: Mapped[Optional["Deal"]] = relationship("Deal", foreign_keys=[deal_id])


class StaffMember(Base):
    __tablename__ = "staff_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    tax_code: Mapped[str] = mapped_column(String(64), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    address: Mapped[str] = mapped_column(String(512), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
