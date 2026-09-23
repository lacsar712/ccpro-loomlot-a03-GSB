from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.vat import Vat


class VatTempSample(Base):
    __tablename__ = "vat_temp_samples"
    __table_args__ = (UniqueConstraint("vat_id", "seq", name="uq_vat_temp_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vat_id: Mapped[int] = mapped_column(ForeignKey("vats.id"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorder_name: Mapped[str] = mapped_column(String(64), nullable=False)

    vat: Mapped["Vat"] = relationship("Vat", back_populates="temp_samples")
