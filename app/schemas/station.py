import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.station import OutletStatus


class OutletOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    index: int
    label: str | None
    status: OutletStatus
    max_power_w: int


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    address: str | None
    latitude: float | None
    longitude: float | None
    is_active: bool


class StationDetailOut(StationOut):
    outlets: list[OutletOut]
    outlets_total: int
    outlets_free_now: int


class AvailabilityQuery(BaseModel):
    duration_minutes: int = Field(gt=0, le=24 * 60, description="Requested session length.")
    not_before: datetime | None = Field(
        default=None,
        description="Earliest acceptable start. Defaults to now (UTC).",
    )


class AvailabilityResponse(BaseModel):
    station_id: uuid.UUID
    available: bool
    outlet_id: uuid.UUID | None = None
    outlet_index: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    wait_minutes: int | None = Field(
        default=None, description="Minutes from `not_before` until the slot opens. 0 = immediate."
    )
