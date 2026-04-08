"""
Data Entry router — Import Excel + Download template + Lịch sử import.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_active_user
from app import models
from app.services.excel_import import HEADERS, parse_excel
from app.services.excel_export import generate_template

router = APIRouter(
    prefix="/data-entry",
    tags=["data-entry"],
    dependencies=[Depends(get_current_active_user)],
)

ALLOWED_MODULES = list(HEADERS.keys())

_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ImportLogOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    module: str
    file_name: str = Field(serialization_alias="fileName")
    total_rows: int = Field(serialization_alias="totalRows")
    success_rows: int = Field(serialization_alias="successRows")
    failed_rows: int = Field(serialization_alias="failedRows")
    errors: list[dict] = Field(default_factory=list)
    status: str
    created_at: datetime = Field(serialization_alias="createdAt")


class ImportResultOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    log_id: str = Field(serialization_alias="logId")
    module: str
    total_rows: int = Field(serialization_alias="totalRows")
    success_rows: int = Field(serialization_alias="successRows")
    failed_rows: int = Field(serialization_alias="failedRows")
    errors: list[dict] = Field(default_factory=list)
    rows: list[dict] = Field(default_factory=list)
    status: str


# ---------------------------------------------------------------------------
# Helper — save import log to DB
# ---------------------------------------------------------------------------

def _save_log(
    db: Session,
    *,
    module: str,
    file_name: str,
    user_id: uuid.UUID,
    total_rows: int,
    success_rows: int,
    failed_rows: int,
    errors: list[dict],
    status: str,
) -> models.DataImportLog:
    log = models.DataImportLog(
        module=module,
        file_name=file_name,
        imported_by=user_id,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=failed_rows,
        errors=errors,
        status=status,
        created_at=_now(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# GET /templates/{module}  — download Excel template mẫu
# ---------------------------------------------------------------------------

@router.get("/templates/{module}")
def download_template(
    module: str = Path(...),
    _user: models.User = Depends(get_current_active_user),
) -> Response:
    if module not in ALLOWED_MODULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module không hỗ trợ. Chọn một trong: {', '.join(ALLOWED_MODULES)}",
        )
    try:
        xlsx_bytes = generate_template(module)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return Response(
        content=xlsx_bytes,
        media_type=_MIME,
        headers={"Content-Disposition": f'attachment; filename="template_{module}.xlsx"'},
    )


# ---------------------------------------------------------------------------
# POST /import/{module}  — import Excel file
# ---------------------------------------------------------------------------

@router.post("/import/{module}", response_model=ImportResultOut, status_code=status.HTTP_201_CREATED)
async def import_module(
    module: str = Path(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_active_user),
) -> ImportResultOut:
    if module not in ALLOWED_MODULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Module không hỗ trợ. Chọn một trong: {', '.join(ALLOWED_MODULES)}",
        )

    # Validate file type
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Chỉ chấp nhận file .xlsx",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File quá lớn (tối đa 10MB)",
        )

    # Parse & validate
    try:
        result = parse_excel(module, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi đọc file: {e}") from e

    errors_list = [{"row": e.row, "column": e.column, "error": e.error} for e in result.errors]
    final_status = "done" if result.failed_rows == 0 else ("failed" if result.success_rows == 0 else "partial")

    # Save log
    log = _save_log(
        db,
        module=module,
        file_name=filename,
        user_id=user.id,
        total_rows=result.total_rows,
        success_rows=result.success_rows,
        failed_rows=result.failed_rows,
        errors=errors_list,
        status=final_status,
    )

    return ImportResultOut(
        log_id=str(log.id),
        module=module,
        total_rows=result.total_rows,
        success_rows=result.success_rows,
        failed_rows=result.failed_rows,
        errors=errors_list,
        rows=result.rows,
        status=final_status,
    )


# ---------------------------------------------------------------------------
# GET /import-logs  — lịch sử import
# ---------------------------------------------------------------------------

@router.get("/import-logs", response_model=list[ImportLogOut])
def list_import_logs(
    module: str | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ImportLogOut]:
    q = db.query(models.DataImportLog).order_by(models.DataImportLog.created_at.desc())
    if module:
        q = q.filter(models.DataImportLog.module == module)
    rows = q.limit(limit).all()
    return [
        ImportLogOut(
            id=str(r.id),
            module=r.module,
            file_name=r.file_name,
            total_rows=r.total_rows,
            success_rows=r.success_rows,
            failed_rows=r.failed_rows,
            errors=r.errors or [],
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /import-logs/{log_id}  — chi tiết 1 lần import
# ---------------------------------------------------------------------------

@router.get("/import-logs/{log_id}", response_model=ImportLogOut)
def get_import_log(
    log_id: UUID,
    db: Session = Depends(get_db),
) -> ImportLogOut:
    r = db.get(models.DataImportLog, log_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return ImportLogOut(
        id=str(r.id),
        module=r.module,
        file_name=r.file_name,
        total_rows=r.total_rows,
        success_rows=r.success_rows,
        failed_rows=r.failed_rows,
        errors=r.errors or [],
        status=r.status,
        created_at=r.created_at,
    )
