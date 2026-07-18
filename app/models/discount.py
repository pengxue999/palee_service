from sqlalchemy import CHAR, Column, DECIMAL, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.configs.database import Base
from app.enums.discount_description import DiscountDescriptionEnum


class Discount(Base):
    __tablename__ = "discount"

    _description_enum = Enum(
        DiscountDescriptionEnum,
        values_callable=lambda items: [item.value for item in items],
    )

    discount_id = Column(CHAR(5), primary_key=True)
    academic_id = Column(
        CHAR(5),
        ForeignKey("academic_years.academic_id", ondelete="RESTRICT"),
        nullable=False,
    )
    discount_amount = Column(DECIMAL(10, 2), nullable=False)
    discount_description = Column(_description_enum, nullable=False)
    threshold_value = Column(Integer, nullable=False, default=0)

    academic_year = relationship("AcademicYear", back_populates="discounts")
    # passive_deletes="all" stops SQLAlchemy nulling registration.discount_id on
    # delete, so the RESTRICT constraint is the thing that actually decides.
    registrations = relationship(
        "Registration", back_populates="discount", passive_deletes="all"
    )
