"""缸温采样链与收染判定。

收染与排液共用 ``evaluate_temp_chain``：缸温链不完整时，既不能收染，
也不能直接排液。
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dye_lot import DyeLot
from app.models.temp_sample import TempSample
from app.models.vat import Vat

# 收染所需的最少连续采样点数
MIN_CHAIN_POINTS = 3
# 相邻采样缸温差绝对值上限（摄氏度，含边界）
MAX_ADJACENT_DELTA = 8.0


def latest_lot_started_at(db: Session, vat: Vat):
    """该缸最新染程开始时刻；无染程返回 None。"""
    return (
        db.query(func.max(DyeLot.started_at))
        .filter(DyeLot.vat_id == vat.id)
        .scalar()
    )


def evaluate_temp_chain(db: Session, vat: Vat):
    """判定缸温采样链是否完整可收染。

    返回 ``(ok: bool, reason: str)``。规则（全部满足才完整）：

    1. 至少连续三个序号采样（序号自 1 起、不断号）；
    2. 相邻采样缸温差绝对值不超过 8℃；
    3. 最新采样晚于该缸最新染程开始时刻。
    """
    samples = (
        db.query(TempSample)
        .filter(TempSample.vat_id == vat.id)
        .order_by(TempSample.seq.asc())
        .all()
    )

    if not samples:
        return False, "该缸尚无缸温采样，链未建立"

    seqs = [s.seq for s in samples]
    if seqs != list(range(1, len(seqs) + 1)):
        return False, "采样序号必须自 1 起连续，当前链存在断号"

    if len(samples) < MIN_CHAIN_POINTS:
        return False, f"缸温链不足 {MIN_CHAIN_POINTS} 个连续采样点，当前 {len(samples)} 点"

    for prev, cur in zip(samples, samples[1:]):
        if abs(cur.temp_c - prev.temp_c) > MAX_ADJACENT_DELTA:
            return False, (
                f"第 {prev.seq}、{cur.seq} 点缸温差 {abs(cur.temp_c - prev.temp_c):g}℃，"
                f"超过相邻温差上限 {MAX_ADJACENT_DELTA:g}℃"
            )

    started_at = latest_lot_started_at(db, vat)
    latest_sample = samples[-1]
    if started_at is None:
        return False, "该缸没有染程记录，无法收染"
    if not (latest_sample.sampled_at > started_at):
        return False, "最新采样不晚于该缸最新染程开始时刻，链未覆盖本染程"

    return True, ""
