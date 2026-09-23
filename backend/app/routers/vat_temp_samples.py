from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.vat import Vat
from app.models.vat_temp_sample import VatTempSample
from app.schemas.vat_temp_sample import (
    VatTempSampleCreate,
    VatTempSampleUpdate,
    VatTempSampleOut,
)

router = APIRouter(prefix="/api/vat-temp-samples", tags=["vat-temp-samples"])


def _get_dyeing_vat_or_409(db: Session, vat_id: int) -> Vat:
    vat = db.query(Vat).filter(Vat.id == vat_id).first()
    if not vat:
        raise HTTPException(status_code=400, detail="染缸不存在")
    if vat.status != "dyeing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"染缸状态为「{vat.status}」，仅染色中染缸可登记缸温采样",
        )
    return vat


@router.get("", response_model=List[VatTempSampleOut])
def list_samples(
    vat_id: Optional[int] = Query(None, alias="vatId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(VatTempSample)
    if vat_id is not None:
        q = q.filter(VatTempSample.vat_id == vat_id)
    return q.order_by(VatTempSample.vat_id, VatTempSample.seq).all()


@router.post("", response_model=VatTempSampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: VatTempSampleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_dyeing_vat_or_409(db, payload.vat_id)
    item = VatTempSample(
        vat_id=payload.vat_id,
        seq=payload.seq,
        temp_c=payload.temp_c,
        sampled_at=payload.sampled_at,
        recorder_name=payload.recorder_name,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=f"该染缸序号 {payload.seq} 的采样已存在"
        )
    db.refresh(item)
    return item


@router.get("/{sample_id}", response_model=VatTempSampleOut)
def get_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(VatTempSample).filter(VatTempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    return item


@router.put("/{sample_id}", response_model=VatTempSampleOut)
def update_sample(
    sample_id: int,
    payload: VatTempSampleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(VatTempSample).filter(VatTempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    data = payload.model_dump(exclude_unset=True)
    if "vat_id" in data and data["vat_id"] != item.vat_id:
        _get_dyeing_vat_or_409(db, data["vat_id"])
    for k, v in data.items():
        setattr(item, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="该染缸采样序号已存在")
    db.refresh(item)
    return item


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(VatTempSample).filter(VatTempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    db.delete(item)
    db.commit()
