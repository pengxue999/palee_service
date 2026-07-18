from pydantic import BaseModel, field_serializer
from typing import Optional

from decimal import Decimal

class DiscountCreate(BaseModel):
    academic_id: str
    discount_amount: Decimal
    discount_description: str
    threshold_value: int

class DiscountUpdate(BaseModel):
    academic_id: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    discount_description: Optional[str] = None
    threshold_value: Optional[int] = None

class DiscountResponse(BaseModel):
    discount_id: str
    discount_amount: Decimal
    discount_description: str
    threshold_value: int
    academic_year: Optional[str]

    @classmethod
    def model_validate(cls, obj):
        desc = obj.discount_description
        desc_val = desc.value if hasattr(desc, "value") else str(desc)
        return cls(
            discount_id=obj.discount_id,
            discount_amount=obj.discount_amount,
            discount_description=desc_val,
            threshold_value=obj.threshold_value,
            academic_year=obj.academic_year.academic_year if obj.academic_year else None
        )
