from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.schemas import CampaignCreate, CampaignOut, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_active_user)])


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)) -> list[CampaignOut]:
    rows = db.query(models.Campaign).all()
    return [CampaignOut.from_row(c) for c in rows]


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)) -> CampaignOut:
    c = db.get(models.Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return CampaignOut.from_row(c)


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db)) -> CampaignOut:
    c = models.Campaign(
        name=body.name,
        channel=body.channel,
        budget=body.budget,
        spent=body.spent,
        start_date=body.start_date,
        end_date=body.end_date,
        leads_generated=body.leads_generated,
        conversions=body.conversions,
        revenue=body.revenue,
        status=body.status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return CampaignOut.from_row(c)


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: UUID, body: CampaignUpdate, db: Session = Depends(get_db)) -> CampaignOut:
    c = db.get(models.Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return CampaignOut.from_row(c)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: UUID, db: Session = Depends(get_db)) -> None:
    c = db.get(models.Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    db.delete(c)
    db.commit()
