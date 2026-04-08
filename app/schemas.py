from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ContactBase(CamelModel):
    name: str
    phone: str = ""
    email: str = ""
    company: str = ""
    address: str = ""
    birthday: Optional[str] = None
    zalo: str = ""
    facebook: str = ""
    tags: list[str] = Field(default_factory=list)
    status: str = "new"
    source: str = ""
    assigned_to: str = ""


class ContactCreate(ContactBase):
    pass


class ContactUpdate(CamelModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[str] = None
    zalo: Optional[str] = None
    facebook: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    source: Optional[str] = None
    assigned_to: Optional[str] = None


class ContactOut(ContactBase):
    id: str
    created_at: date = Field(serialization_alias="createdAt")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @classmethod
    def from_row(cls, c: Any) -> ContactOut:
        return cls(
            id=str(c.id),
            name=c.name,
            phone=c.phone,
            email=c.email,
            company=c.company,
            address=c.address,
            birthday=c.birthday,
            zalo=c.zalo,
            facebook=c.facebook,
            tags=list(c.tags or []),
            status=c.status,
            source=c.source,
            assigned_to=c.assigned_to,
            created_at=c.created_at,
        )


class DealBase(CamelModel):
    title: str
    value: Decimal = Decimal(0)
    contact_id: UUID
    assigned_to: str = ""
    stage: str = "new_lead"
    probability: int = 0
    close_date: Optional[str] = None
    notes: str = ""


class DealCreate(CamelModel):
    title: str
    value: Decimal = Decimal(0)
    contact_id: UUID
    assigned_to: str = ""
    stage: str = "new_lead"
    probability: int = 0
    close_date: Optional[str] = None
    notes: str = ""


class DealUpdate(CamelModel):
    title: Optional[str] = None
    value: Optional[Decimal] = None
    contact_id: Optional[UUID] = None
    assigned_to: Optional[str] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    close_date: Optional[str] = None
    notes: Optional[str] = None


class DealOut(CamelModel):
    id: str
    title: str
    value: Decimal
    contact_id: str = Field(serialization_alias="contactId")
    contact_name: str = Field(serialization_alias="contactName")
    assigned_to: str = Field(serialization_alias="assignedTo")
    stage: str
    probability: int
    close_date: Optional[str] = Field(serialization_alias="closeDate")
    notes: str
    created_at: date = Field(serialization_alias="createdAt")

    @classmethod
    def from_row(cls, d: Any) -> DealOut:
        cn = d.contact.name if getattr(d, "contact", None) else ""
        return cls(
            id=str(d.id),
            title=d.title,
            value=d.value,
            contact_id=str(d.contact_id),
            contact_name=cn,
            assigned_to=d.assigned_to,
            stage=d.stage,
            probability=d.probability,
            close_date=d.close_date,
            notes=d.notes,
            created_at=d.created_at,
        )


class DealStagePatch(CamelModel):
    stage: str


class TaskBase(CamelModel):
    title: str
    status: str = "todo"
    priority: str = "medium"
    assigned_to: str = ""
    due_date: Optional[str] = None
    linked_contact_id: Optional[UUID] = Field(default=None, serialization_alias="linkedContactId")
    linked_deal_id: Optional[UUID] = Field(default=None, serialization_alias="linkedDealId")


class TaskCreate(CamelModel):
    title: str
    status: str = "todo"
    priority: str = "medium"
    assigned_to: str = ""
    due_date: Optional[str] = None
    linked_contact_id: Optional[UUID] = None
    linked_deal_id: Optional[UUID] = None


class TaskUpdate(CamelModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    linked_contact_id: Optional[UUID] = None
    linked_deal_id: Optional[UUID] = None


class TaskOut(CamelModel):
    id: str
    title: str
    status: str
    priority: str
    assigned_to: str = Field(serialization_alias="assignedTo")
    due_date: Optional[str] = Field(serialization_alias="dueDate")
    linked_contact: Optional[str] = Field(default=None, serialization_alias="linkedContact")
    linked_deal: Optional[str] = Field(default=None, serialization_alias="linkedDeal")

    @classmethod
    def from_row(cls, t: Any) -> TaskOut:
        lc = t.linked_contact.name if getattr(t, "linked_contact", None) else None
        ld = t.linked_deal.title if getattr(t, "linked_deal", None) else None
        return cls(
            id=str(t.id),
            title=t.title,
            status=t.status,
            priority=t.priority,
            assigned_to=t.assigned_to,
            due_date=t.due_date,
            linked_contact=lc,
            linked_deal=ld,
        )


class CampaignBase(CamelModel):
    name: str
    channel: str = ""
    budget: Decimal = Decimal(0)
    spent: Decimal = Decimal(0)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    leads_generated: int = 0
    conversions: int = 0
    revenue: Decimal = Decimal(0)
    status: str = "active"


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(CamelModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    budget: Optional[Decimal] = None
    spent: Optional[Decimal] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    leads_generated: Optional[int] = None
    conversions: Optional[int] = None
    revenue: Optional[Decimal] = None
    status: Optional[str] = None


class CampaignOut(CampaignBase):
    id: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @classmethod
    def from_row(cls, c: Any) -> CampaignOut:
        return cls(
            id=str(c.id),
            name=c.name,
            channel=c.channel,
            budget=c.budget,
            spent=c.spent,
            start_date=c.start_date,
            end_date=c.end_date,
            leads_generated=c.leads_generated,
            conversions=c.conversions,
            revenue=c.revenue,
            status=c.status,
        )


class ActivityOut(CamelModel):
    id: str
    type: str
    description: str
    contact_name: Optional[str] = Field(default=None, serialization_alias="contactName")
    time: str
    user: str
    occurred_at: Optional[datetime] = Field(default=None, serialization_alias="occurredAt")
    contact_id: Optional[str] = Field(default=None, serialization_alias="contactId")
    deal_id: Optional[str] = Field(default=None, serialization_alias="dealId")
    deal_title: Optional[str] = Field(default=None, serialization_alias="dealTitle")

    @classmethod
    def from_row(cls, a: Any) -> ActivityOut:
        deal_title = None
        if getattr(a, "deal", None):
            deal_title = a.deal.title
        return cls(
            id=str(a.id),
            type=a.type,
            description=a.description,
            contact_name=a.contact_name,
            time=a.time,
            user=a.user,
            occurred_at=getattr(a, "occurred_at", None),
            contact_id=str(a.contact_id) if getattr(a, "contact_id", None) else None,
            deal_id=str(a.deal_id) if getattr(a, "deal_id", None) else None,
            deal_title=deal_title,
        )


class ActivityCreate(CamelModel):
    type: str
    description: str
    contact_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None


class PipelineStageOut(CamelModel):
    id: str
    label: str
    color: str


class MetaOut(CamelModel):
    staff_members: list[str] = Field(serialization_alias="staffMembers")
    pipeline_stages: list[PipelineStageOut] = Field(serialization_alias="pipelineStages")


class LoginIn(CamelModel):
    email: str
    password: str


class TokenOut(CamelModel):
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(serialization_alias="tokenType", default="bearer")


class UserPublic(CamelModel):
    id: str
    email: str
    full_name: str = Field(serialization_alias="fullName")
    role: str = "staff"


class UserCreate(CamelModel):
    email: str
    password: str
    full_name: str = Field(default="", serialization_alias="fullName")
    role: str = "staff"
    is_active: bool = Field(default=True, serialization_alias="isActive")


class UserUpdate(CamelModel):
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = Field(default=None, serialization_alias="fullName")
    role: Optional[str] = None
    is_active: Optional[bool] = Field(default=None, serialization_alias="isActive")


class PaginatedContacts(CamelModel):
    items: list[ContactOut]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")


class PaginatedDeals(CamelModel):
    items: list[DealOut]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")


class PaginatedTasks(CamelModel):
    items: list[TaskOut]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")


class CompanyOut(CamelModel):
    company_name: str = Field(serialization_alias="companyName")
    tax_code: str = Field(serialization_alias="taxCode")
    email: str
    phone: str
    address: str
    website: str

    @classmethod
    def from_row(cls, row: Any) -> "CompanyOut":
        return cls(
            company_name=row.company_name,
            tax_code=row.tax_code,
            email=row.email,
            phone=row.phone,
            address=row.address,
            website=row.website,
        )


class CompanyUpdate(CamelModel):
    company_name: Optional[str] = None
    tax_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None


class StaffMemberOut(CamelModel):
    id: str
    name: str
    sort_order: int = Field(serialization_alias="sortOrder")

    @classmethod
    def from_row(cls, s: Any) -> "StaffMemberOut":
        return cls(id=str(s.id), name=s.name, sort_order=s.sort_order)


class StaffMemberCreate(CamelModel):
    name: str
    sort_order: int = Field(default=0, serialization_alias="sortOrder")


class StaffMemberUpdate(CamelModel):
    name: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, serialization_alias="sortOrder")


class SearchHit(CamelModel):
    id: str
    kind: str
    title: str
    subtitle: str = ""


class SearchOut(CamelModel):
    contacts: list[SearchHit]
    deals: list[SearchHit]
    tasks: list[SearchHit]


class NotificationItem(CamelModel):
    id: str
    kind: str
    title: str
    subtitle: str = ""
    due_date: Optional[str] = Field(default=None, serialization_alias="dueDate")
    task_id: Optional[str] = Field(default=None, serialization_alias="taskId")


class ImportContactsResult(CamelModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class EmailTestIn(CamelModel):
    to: str
    subject: str = "CRM Việt — thử nghiệm SMTP"
    body: str = "Đây là email thử từ CRM."


class DashboardKpisOut(CamelModel):
    contacts_total: int = Field(serialization_alias="contactsTotal")
    active_leads: int = Field(serialization_alias="activeLeads")
    tasks_open: int = Field(serialization_alias="tasksOpen")
    tasks_due_today: int = Field(serialization_alias="tasksDueToday")
    won_this_month: int = Field(serialization_alias="wonThisMonth")
    lost_this_month: int = Field(serialization_alias="lostThisMonth")
    win_rate_this_month: int = Field(serialization_alias="winRateThisMonth")
    revenue_won_total: float = Field(serialization_alias="revenueWonTotal")
    revenue_forecast: float = Field(serialization_alias="revenueForecast")


class SmtpSettingsOut(CamelModel):
    host: str
    port: int
    user: str
    from_email: str = Field(serialization_alias="fromEmail")
    use_tls: bool = Field(serialization_alias="useTls")


class SmtpSettingsUpdate(CamelModel):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = Field(default=None, serialization_alias="fromEmail")
    use_tls: Optional[bool] = Field(default=None, serialization_alias="useTls")
