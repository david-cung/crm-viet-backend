from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models
from app.security import hash_password


def ensure_default_admin(db: Session) -> None:
    if db.query(models.User).filter(models.User.email == "admin@crm.local").first():
        return
    db.add(
        models.User(
            email="admin@crm.local",
            hashed_password=hash_password("changeme"),
            full_name="Quản trị",
            is_active=True,
            role="admin",
        )
    )
    db.commit()


def ensure_company_defaults(db: Session) -> None:
    if db.get(models.CompanySettings, 1) is not None:
        return
    db.add(
        models.CompanySettings(
            id=1,
            company_name="CRM Việt Corp",
            tax_code="",
            email="info@crmviet.vn",
            phone="028 1234 5678",
            address="123 Nguyễn Huệ, Q1, TP.HCM",
            website="https://crmviet.vn",
        )
    )
    db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(models.Contact).first() is not None:
        return

    staff_names = [
        "Nguyễn Văn An",
        "Trần Thị Bích",
        "Lê Minh Cường",
        "Phạm Thùy Dung",
        "Hoàng Đức Em",
    ]
    for i, name in enumerate(staff_names):
        db.add(models.StaffMember(name=name, sort_order=i))

    contacts_payload = [
        {
            "name": "Nguyễn Thị Hương",
            "phone": "0901234567",
            "email": "huong@techvina.vn",
            "company": "TechVina JSC",
            "address": "Q1, TP.HCM",
            "birthday": "1990-03-15",
            "zalo": "0901234567",
            "facebook": "huong.nguyen",
            "tags": ["VIP", "Công nghệ"],
            "status": "vip",
            "source": "Facebook Ads",
            "assigned_to": "Nguyễn Văn An",
            "created_at": date(2024, 1, 10),
        },
        {
            "name": "Trần Văn Minh",
            "phone": "0912345678",
            "email": "minh@greenfoods.vn",
            "company": "Green Foods",
            "address": "Q7, TP.HCM",
            "birthday": "1985-07-22",
            "zalo": "0912345678",
            "facebook": "minh.tran",
            "tags": ["Tiềm năng", "F&B"],
            "status": "active",
            "source": "Zalo OA",
            "assigned_to": "Trần Thị Bích",
            "created_at": date(2024, 2, 5),
        },
        {
            "name": "Lê Thị Lan",
            "phone": "0923456789",
            "email": "lan@fashionhub.vn",
            "company": "Fashion Hub",
            "address": "Q3, TP.HCM",
            "birthday": "1992-11-08",
            "zalo": "0923456789",
            "facebook": "lan.le",
            "tags": ["Mới", "Thời trang"],
            "status": "new",
            "source": "Google Ads",
            "assigned_to": "Lê Minh Cường",
            "created_at": date(2024, 3, 12),
        },
        {
            "name": "Phạm Đức Anh",
            "phone": "0934567890",
            "email": "anh@buildpro.vn",
            "company": "BuildPro",
            "address": "Q2, TP.HCM",
            "birthday": "1988-05-30",
            "zalo": "0934567890",
            "facebook": "anh.pham",
            "tags": ["VIP", "Xây dựng"],
            "status": "vip",
            "source": "Giới thiệu",
            "assigned_to": "Nguyễn Văn An",
            "created_at": date(2024, 1, 20),
        },
        {
            "name": "Hoàng Thị Mai",
            "phone": "0945678901",
            "email": "mai@edulearn.vn",
            "company": "EduLearn",
            "address": "Cầu Giấy, HN",
            "birthday": "1995-09-14",
            "zalo": "0945678901",
            "facebook": "mai.hoang",
            "tags": ["Tiềm năng", "Giáo dục"],
            "status": "active",
            "source": "Email",
            "assigned_to": "Phạm Thùy Dung",
            "created_at": date(2024, 2, 28),
        },
        {
            "name": "Vũ Quốc Bảo",
            "phone": "0956789012",
            "email": "bao@logisticvn.vn",
            "company": "Logistic VN",
            "address": "Long Biên, HN",
            "birthday": "1987-12-03",
            "zalo": "0956789012",
            "facebook": "bao.vu",
            "tags": ["Không hoạt động"],
            "status": "inactive",
            "source": "Facebook Ads",
            "assigned_to": "Hoàng Đức Em",
            "created_at": date(2023, 11, 15),
        },
        {
            "name": "Đỗ Thanh Tùng",
            "phone": "0967890123",
            "email": "tung@mediapro.vn",
            "company": "MediaPro",
            "address": "Đống Đa, HN",
            "birthday": "1991-06-18",
            "zalo": "0967890123",
            "facebook": "tung.do",
            "tags": ["Mới", "Truyền thông"],
            "status": "new",
            "source": "Zalo OA",
            "assigned_to": "Trần Thị Bích",
            "created_at": date(2024, 3, 20),
        },
        {
            "name": "Bùi Thị Ngọc",
            "phone": "0978901234",
            "email": "ngoc@healthplus.vn",
            "company": "HealthPlus",
            "address": "Q10, TP.HCM",
            "birthday": "1993-01-25",
            "zalo": "0978901234",
            "facebook": "ngoc.bui",
            "tags": ["Tiềm năng", "Y tế"],
            "status": "active",
            "source": "Google Ads",
            "assigned_to": "Lê Minh Cường",
            "created_at": date(2024, 3, 1),
        },
    ]

    contact_objs: list[models.Contact] = []
    for p in contacts_payload:
        c = models.Contact(**p)
        db.add(c)
        contact_objs.append(c)
    db.flush()

    deals_payload = [
        {
            "title": "Hệ thống ERP cho TechVina",
            "value": Decimal("450000000"),
            "contact_idx": 0,
            "assigned_to": "Nguyễn Văn An",
            "stage": "negotiation",
            "probability": 70,
            "close_date": "2024-04-30",
            "notes": "Khách hàng quan tâm module kế toán",
            "created_at": date(2024, 2, 1),
        },
        {
            "title": "Website thương mại Green Foods",
            "value": Decimal("85000000"),
            "contact_idx": 1,
            "assigned_to": "Trần Thị Bích",
            "stage": "proposal",
            "probability": 50,
            "close_date": "2024-04-15",
            "notes": "Cần demo lại lần 2",
            "created_at": date(2024, 2, 15),
        },
        {
            "title": "App quản lý kho Fashion Hub",
            "value": Decimal("120000000"),
            "contact_idx": 2,
            "assigned_to": "Lê Minh Cường",
            "stage": "qualified",
            "probability": 40,
            "close_date": "2024-05-10",
            "notes": "Đang so sánh với đối thủ",
            "created_at": date(2024, 3, 1),
        },
        {
            "title": "Phần mềm quản lý dự án BuildPro",
            "value": Decimal("280000000"),
            "contact_idx": 3,
            "assigned_to": "Nguyễn Văn An",
            "stage": "won",
            "probability": 100,
            "close_date": "2024-03-20",
            "notes": "Đã ký hợp đồng",
            "created_at": date(2024, 1, 25),
        },
        {
            "title": "Platform học trực tuyến EduLearn",
            "value": Decimal("200000000"),
            "contact_idx": 4,
            "assigned_to": "Phạm Thùy Dung",
            "stage": "contacted",
            "probability": 20,
            "close_date": "2024-05-30",
            "notes": "Mới trao đổi sơ bộ",
            "created_at": date(2024, 3, 10),
        },
        {
            "title": "Hệ thống tracking Logistic VN",
            "value": Decimal("350000000"),
            "contact_idx": 5,
            "assigned_to": "Hoàng Đức Em",
            "stage": "lost",
            "probability": 0,
            "close_date": "2024-03-01",
            "notes": "Khách chọn vendor khác",
            "created_at": date(2023, 12, 1),
        },
        {
            "title": "CRM cho MediaPro",
            "value": Decimal("95000000"),
            "contact_idx": 6,
            "assigned_to": "Trần Thị Bích",
            "stage": "new_lead",
            "probability": 10,
            "close_date": "2024-06-15",
            "notes": "Lead từ Zalo",
            "created_at": date(2024, 3, 22),
        },
        {
            "title": "App đặt lịch HealthPlus",
            "value": Decimal("150000000"),
            "contact_idx": 7,
            "assigned_to": "Lê Minh Cường",
            "stage": "new_lead",
            "probability": 15,
            "close_date": "2024-06-01",
            "notes": "Khách cần tư vấn thêm",
            "created_at": date(2024, 3, 5),
        },
    ]

    deal_objs: list[models.Deal] = []
    for p in deals_payload:
        idx = p.pop("contact_idx")
        d = models.Deal(
            contact_id=contact_objs[idx].id,
            title=p["title"],
            value=p["value"],
            assigned_to=p["assigned_to"],
            stage=p["stage"],
            probability=p["probability"],
            close_date=p["close_date"],
            notes=p["notes"],
            created_at=p["created_at"],
        )
        db.add(d)
        deal_objs.append(d)
    db.flush()

    tasks_payload = [
        {
            "title": "Gọi điện follow-up TechVina",
            "status": "todo",
            "priority": "high",
            "assigned_to": "Nguyễn Văn An",
            "due_date": "2024-04-03",
            "lc": 0,
            "ld": 0,
        },
        {
            "title": "Gửi báo giá Green Foods",
            "status": "in_progress",
            "priority": "high",
            "assigned_to": "Trần Thị Bích",
            "due_date": "2024-04-02",
            "lc": 1,
            "ld": 1,
        },
        {
            "title": "Chuẩn bị demo Fashion Hub",
            "status": "todo",
            "priority": "medium",
            "assigned_to": "Lê Minh Cường",
            "due_date": "2024-04-05",
            "lc": 2,
            "ld": None,
        },
        {
            "title": "Cập nhật hợp đồng BuildPro",
            "status": "done",
            "priority": "high",
            "assigned_to": "Nguyễn Văn An",
            "due_date": "2024-03-25",
            "lc": None,
            "ld": 3,
        },
        {
            "title": "Soạn proposal EduLearn",
            "status": "todo",
            "priority": "medium",
            "assigned_to": "Phạm Thùy Dung",
            "due_date": "2024-04-08",
            "lc": 4,
            "ld": None,
        },
        {
            "title": "Follow-up HealthPlus sau demo",
            "status": "todo",
            "priority": "low",
            "assigned_to": "Lê Minh Cường",
            "due_date": "2024-04-10",
            "lc": 7,
            "ld": None,
        },
    ]

    for p in tasks_payload:
        lc = p.pop("lc")
        ld = p.pop("ld")
        t = models.Task(
            title=p["title"],
            status=p["status"],
            priority=p["priority"],
            assigned_to=p["assigned_to"],
            due_date=p["due_date"],
            linked_contact_id=contact_objs[lc].id if lc is not None else None,
            linked_deal_id=deal_objs[ld].id if ld is not None else None,
        )
        db.add(t)

    campaigns_payload = [
        {
            "name": "Quảng cáo Tết 2024",
            "channel": "Facebook Ads",
            "budget": Decimal("50000000"),
            "spent": Decimal("42000000"),
            "start_date": "2024-01-15",
            "end_date": "2024-02-15",
            "leads_generated": 120,
            "conversions": 18,
            "revenue": Decimal("450000000"),
            "status": "completed",
        },
        {
            "name": "Ra mắt sản phẩm mới",
            "channel": "Google Ads",
            "budget": Decimal("30000000"),
            "spent": Decimal("28000000"),
            "start_date": "2024-02-01",
            "end_date": "2024-03-31",
            "leads_generated": 85,
            "conversions": 12,
            "revenue": Decimal("280000000"),
            "status": "completed",
        },
        {
            "name": "Zalo OA tháng 3",
            "channel": "Zalo OA",
            "budget": Decimal("15000000"),
            "spent": Decimal("8000000"),
            "start_date": "2024-03-01",
            "end_date": "2024-03-31",
            "leads_generated": 45,
            "conversions": 7,
            "revenue": Decimal("95000000"),
            "status": "active",
        },
        {
            "name": "Email nurturing Q1",
            "channel": "Email",
            "budget": Decimal("5000000"),
            "spent": Decimal("3500000"),
            "start_date": "2024-01-01",
            "end_date": "2024-03-31",
            "leads_generated": 30,
            "conversions": 5,
            "revenue": Decimal("120000000"),
            "status": "active",
        },
        {
            "name": "Chương trình giới thiệu",
            "channel": "Giới thiệu",
            "budget": Decimal("10000000"),
            "spent": Decimal("6000000"),
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "leads_generated": 25,
            "conversions": 10,
            "revenue": Decimal("350000000"),
            "status": "active",
        },
    ]
    for p in campaigns_payload:
        db.add(models.Campaign(**p))

    activities_payload = [
        {
            "type": "call",
            "description": "Gọi điện cho Nguyễn Thị Hương - thảo luận ERP",
            "contact_name": "Nguyễn Thị Hương",
            "time": "10 phút trước",
            "user": "Nguyễn Văn An",
            "contact_idx": 0,
            "deal_idx": 0,
        },
        {
            "type": "deal",
            "description": 'Chuyển deal "Website Green Foods" sang Gửi báo giá',
            "contact_name": "Trần Văn Minh",
            "time": "30 phút trước",
            "user": "Trần Thị Bích",
            "contact_idx": 1,
            "deal_idx": 1,
        },
        {
            "type": "email",
            "description": "Gửi email proposal cho Fashion Hub",
            "contact_name": "Lê Thị Lan",
            "time": "1 giờ trước",
            "user": "Lê Minh Cường",
            "contact_idx": 2,
            "deal_idx": 2,
        },
        {
            "type": "note",
            "description": 'Thêm ghi chú: "Khách hàng cần thêm tính năng báo cáo"',
            "contact_name": "Phạm Đức Anh",
            "time": "2 giờ trước",
            "user": "Nguyễn Văn An",
            "contact_idx": 3,
            "deal_idx": 3,
        },
        {
            "type": "task",
            "description": 'Hoàn thành task "Cập nhật hợp đồng BuildPro"',
            "contact_name": None,
            "time": "3 giờ trước",
            "user": "Nguyễn Văn An",
            "contact_idx": None,
            "deal_idx": 3,
        },
        {
            "type": "message",
            "description": "Nhận tin nhắn Zalo từ Hoàng Thị Mai",
            "contact_name": "Hoàng Thị Mai",
            "time": "4 giờ trước",
            "user": "Phạm Thùy Dung",
            "contact_idx": 4,
            "deal_idx": None,
        },
    ]
    for p in activities_payload:
        ci = p.pop("contact_idx", None)
        di = p.pop("deal_idx", None)
        db.add(
            models.Activity(
                contact_id=contact_objs[ci].id if ci is not None else None,
                deal_id=deal_objs[di].id if di is not None else None,
                **p,
            )
        )

    db.commit()
