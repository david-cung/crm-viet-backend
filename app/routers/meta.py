from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.schemas import MetaOut, PipelineStageOut

router = APIRouter(prefix="/meta", tags=["meta"], dependencies=[Depends(get_current_active_user)])

PIPELINE_STAGES = [
    PipelineStageOut(id="new_lead", label="Lead mới", color="status-new"),
    PipelineStageOut(id="contacted", label="Đã liên hệ", color="status-contacted"),
    PipelineStageOut(id="qualified", label="Đủ điều kiện", color="status-qualified"),
    PipelineStageOut(id="proposal", label="Gửi báo giá", color="status-proposal"),
    PipelineStageOut(id="negotiation", label="Đàm phán", color="status-negotiation"),
    PipelineStageOut(id="won", label="Thắng", color="status-won"),
    PipelineStageOut(id="lost", label="Thua", color="status-lost"),
]


@router.get("", response_model=MetaOut)
def get_meta(db: Session = Depends(get_db)) -> MetaOut:
    staff_rows = db.query(models.StaffMember).order_by(models.StaffMember.sort_order).all()
    names = [s.name for s in staff_rows]
    return MetaOut(staff_members=names, pipeline_stages=PIPELINE_STAGES)
