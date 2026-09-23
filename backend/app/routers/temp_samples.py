from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.temp_sample import TempSample
from app.models.user import User
from app.models.vat import Vat
from app.schemas.temp_sample import TempSampleCreate, TempSampleUpdate, TempSampleOut

router = APIRouter(prefix="/api/temp-samples", tags=["temp-samples"])


def _get_dyeing_vat(db: Session, vat_id: int) -> Vat:
    vat = db.query(Vat).filter(Vat.id == vat_id).first()
    if not vat:
        raise HTTPException(status_code=400, detail="染缸不存在")
    if vat.status != "dyeing":
        raise HTTPException(
            status_code=409,
            detail=f"染缸当前为「{vat.status}」状态，仅染程中（dyeing）染缸可登记缸温采样",
        )
    return vat


@router.get("", response_model=List[TempSampleOut])
def list_samples(
    vat_id: Optional[int] = Query(None, alias="vatId"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(TempSample)
    if vat_id is not None:
        q = q.filter(TempSample.vat_id == vat_id)
    return q.order_by(TempSample.vat_id, TempSample.seq).all()


@router.post("", response_model=TempSampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: TempSampleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_dyeing_vat(db, payload.vat_id)
    item = TempSample(
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
        raise HTTPException(status_code=400, detail="同缸采样序号已存在")
    db.refresh(item)
    return item


@router.get("/{sample_id}", response_model=TempSampleOut)
def get_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(TempSample).filter(TempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    return item


@router.put("/{sample_id}", response_model=TempSampleOut)
def update_sample(
    sample_id: int,
    payload: TempSampleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(TempSample).filter(TempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    data = payload.model_dump(exclude_unset=True)
    target_vat_id = data.get("vat_id", item.vat_id)
    # 采样属于染程中的缸：改挂或改序号时，目标缸必须仍在染程中
    _get_dyeing_vat(db, target_vat_id)
    for k, v in data.items():
        setattr(item, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同缸采样序号已存在")
    db.refresh(item)
    return item


@router.delete("/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(TempSample).filter(TempSample.id == sample_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="缸温采样不存在")
    db.delete(item)
    db.commit()
