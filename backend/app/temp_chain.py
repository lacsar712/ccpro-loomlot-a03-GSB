"""缸温采样链判定：收染（finish）与排液（drain）共用。

规则（任一不满足即 409，中文提示）：
1. 该缸至少存在三个序号连续的采样（序号从 1 起、同缸唯一）；
2. 连续链内相邻采样缸温差绝对值不超过 8℃；
3. 最新采样时刻晚于该缸最新染程开始时刻。
"""

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.dye_lot import DyeLot
from app.models.vat import Vat
from app.models.vat_temp_sample import VatTempSample

MIN_CHAIN_SAMPLES = 3
MAX_TEMP_DELTA_C = 8.0


def longest_consecutive_run(samples: List[VatTempSample]) -> List[VatTempSample]:
    """按序号升序，返回最长的序号连续（步长为 1）采样段。"""
    best: List[VatTempSample] = []
    cur: List[VatTempSample] = []
    for s in samples:
        if cur and s.seq != cur[-1].seq + 1:
            cur = []
        cur.append(s)
        if len(cur) > len(best):
            best = list(cur)
    return best


def ensure_temp_chain_finished(db: Session, vat: Vat) -> List[VatTempSample]:
    """校验缸温采样链是否满足收染条件；不满足抛 409，满足返回连续链。"""
    samples = (
        db.query(VatTempSample)
        .filter(VatTempSample.vat_id == vat.id)
        .order_by(VatTempSample.seq)
        .all()
    )
    run = longest_consecutive_run(samples)
    if len(run) < MIN_CHAIN_SAMPLES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"缸温采样链未闭合：染缸「{vat.vat_code}」最长连续序号采样仅 "
                f"{len(run)} 点，收染需至少 {MIN_CHAIN_SAMPLES} 个连续序号采样"
            ),
        )
    for prev, cur in zip(run, run[1:]):
        delta = abs(cur.temp_c - prev.temp_c)
        if delta > MAX_TEMP_DELTA_C:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"缸温采样链温差超限：序号 {prev.seq}→{cur.seq} 相邻缸温差 "
                    f"{delta:.1f}℃，超过允许的 {MAX_TEMP_DELTA_C:.0f}℃"
                ),
            )
    latest_sampled_at = max(s.sampled_at for s in samples)
    latest_lot = (
        db.query(DyeLot)
        .filter(DyeLot.vat_id == vat.id)
        .order_by(DyeLot.started_at.desc())
        .first()
    )
    if latest_lot is not None and latest_sampled_at <= latest_lot.started_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="缸温采样链过旧：最新采样时刻未晚于该缸最新染程开始时刻，无法收染",
        )
    return run
