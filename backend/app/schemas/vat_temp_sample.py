from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VatTempSampleCreate(BaseModel):
    vat_id: int = Field(..., alias="vatId")
    seq: int = Field(..., ge=1)
    temp_c: float = Field(..., alias="tempC")
    sampled_at: datetime = Field(..., alias="sampledAt")
    recorder_name: str = Field(..., min_length=1, max_length=64, alias="recorderName")

    model_config = ConfigDict(populate_by_name=True)


class VatTempSampleUpdate(BaseModel):
    vat_id: Optional[int] = Field(None, alias="vatId")
    seq: Optional[int] = Field(None, ge=1)
    temp_c: Optional[float] = Field(None, alias="tempC")
    sampled_at: Optional[datetime] = Field(None, alias="sampledAt")
    recorder_name: Optional[str] = Field(None, min_length=1, max_length=64, alias="recorderName")

    model_config = ConfigDict(populate_by_name=True)


class VatTempSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    vat_id: int = Field(serialization_alias="vatId")
    seq: int
    temp_c: float = Field(serialization_alias="tempC")
    sampled_at: datetime = Field(serialization_alias="sampledAt")
    recorder_name: str = Field(serialization_alias="recorderName")
