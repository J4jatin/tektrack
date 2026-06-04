"""TekTrack - Pydantic models."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from backend.database import VALID_STATUSES


class OrderCreate(BaseModel):
    id: str = Field(..., pattern=r"^TK-\d{4}-\d{3,6}$")
    customer: str = Field(..., min_length=2, max_length=120)
    mask_type: str = Field(..., min_length=2, max_length=60)
    layer: str = Field(..., min_length=1, max_length=60)
    quantity: int = Field(..., gt=0, le=1000)
    priority: str = Field(default="NORMAL")
    engineer: str = Field(..., min_length=2, max_length=80)
    notes: Optional[str] = Field(default="", max_length=500)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v not in {"NORMAL", "HIGH", "CRITICAL"}:
            raise ValueError("priority must be NORMAL, HIGH, or CRITICAL")
        return v


class StatusUpdate(BaseModel):
    new_status: str
    changed_by: Optional[str] = "frontend"

    @field_validator("new_status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {v}")
        return v


class OrderResponse(BaseModel):
    id: str
    customer: str
    mask_type: str
    layer: str
    quantity: int
    priority: str
    status: str
    engineer: str
    notes: str
    created_at: str
    updated_at: str


class StatusLogEntry(BaseModel):
    log_id: int
    order_id: str
    old_status: Optional[str]
    new_status: str
    changed_at: str
    changed_by: str


class AnalyticsSummary(BaseModel):
    total_orders: int
    by_status: dict
    by_priority: dict
    by_customer: dict
    critical_in_progress: int
