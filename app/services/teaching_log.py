from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from app.models.teaching_log import TeachingLog
from app.models.teacher_assignment import TeacherAssignment
from app.models.subject_detail import SubjectDetail
from app.models.academic_years import AcademicYear
from app.enums.academic_status import AcademicStatusEnum
from app.schemas.teaching_log import TeachingLogCreate, TeachingLogUpdate
from app.configs.exceptions import NotFoundException, ValidationException


TEACHING_STATUS = 'TEACHING'
ABSENT_STATUS = 'ABSENT'

NO_ACTIVE_YEAR_MESSAGE = "ບໍ່ມີສົກຮຽນທີ່ກຳລັງດຳເນີນການ, ບໍ່ສາມາດບັນທຶກການສອນໄດ້"
INACTIVE_YEAR_MESSAGE = "ບັນທຶກການສອນໄດ້ສະເພາະສົກຮຽນທີ່ກຳລັງດຳເນີນການເທົ່ານັ້ນ"


def _get_active_academic_year(db: Session) -> AcademicYear | None:
    return db.query(AcademicYear).filter(
        AcademicYear.status == AcademicStatusEnum.ACTIVE
    ).first()


def _assert_assignment_in_active_year(db: Session, assignment_id: str):
    """ບັນທຶກການສອນຕ້ອງອີງໃສ່ການມອບໝາຍຂອງສົກຮຽນທີ່ ACTIVE ເທົ່ານັ້ນ."""
    active_year = _get_active_academic_year(db)
    if not active_year:
        raise ValidationException(NO_ACTIVE_YEAR_MESSAGE)

    assignment = db.query(TeacherAssignment).filter(
        TeacherAssignment.assignment_id == assignment_id
    ).first()
    if not assignment:
        raise NotFoundException("ຂໍ້ມູນການສອນຂອງອາຈານ")
    if assignment.academic_id != active_year.academic_id:
        raise ValidationException(INACTIVE_YEAR_MESSAGE)
    return assignment


def _query_with_relations(db: Session):
    return db.query(TeachingLog).options(
        joinedload(TeachingLog.assignment).joinedload(TeacherAssignment.teacher),
        joinedload(TeachingLog.assignment).joinedload(TeacherAssignment.subject_detail).joinedload(SubjectDetail.subject),
        joinedload(TeachingLog.assignment).joinedload(TeacherAssignment.subject_detail).joinedload(SubjectDetail.level),
        joinedload(TeachingLog.assignment).joinedload(TeacherAssignment.academic_year),
        joinedload(TeachingLog.substitute_assignment).joinedload(TeacherAssignment.teacher),
        joinedload(TeachingLog.substitute_assignment).joinedload(TeacherAssignment.subject_detail).joinedload(SubjectDetail.subject),
    )


def _resolve_academic_year(db: Session, academic_year: str = None) -> str | None:
    """ບໍ່ລະບຸສົກຮຽນ = ໃຊ້ສົກທີ່ ACTIVE. ບໍ່ມີສົກ ACTIVE = ບໍ່ຄວນສະແດງຂໍ້ມູນໃດໆ."""
    if academic_year:
        return academic_year
    active_year = _get_active_academic_year(db)
    return active_year.academic_year if active_year else None


def get_all(
    db: Session,
    academic_year: str = None,
    month: str = None,
    status: str = None,
    teacher_id: str = None
):
    from sqlalchemy import desc, case
    academic_year = _resolve_academic_year(db, academic_year)
    if not academic_year:
        return []

    query = _query_with_relations(db).join(
        TeacherAssignment, TeachingLog.assignment_id == TeacherAssignment.assignment_id
    ).join(
        AcademicYear, TeacherAssignment.academic_id == AcademicYear.academic_id
    ).filter(AcademicYear.academic_year == academic_year)

    if teacher_id:
        query = query.filter(TeacherAssignment.teacher_id == teacher_id)

    if status:
        query = query.filter(TeachingLog.status == status)

    if month:
        from sqlalchemy import extract
        year, mon = month.split('-')
        query = query.filter(
            extract('year', TeachingLog.teaching_date) == int(year)
        ).filter(
            extract('month', TeachingLog.teaching_date) == int(mon)
        )

    query = query.order_by(
        desc(TeachingLog.teaching_date),
        case((TeachingLog.status == ABSENT_STATUS, 1), else_=0).desc()
    )
    return query.all()


def get_by_teacher(db: Session, teacher_id: str, academic_year: str = None, from_date: str = None, to_date: str = None):
    from sqlalchemy import desc, case
    academic_year = _resolve_academic_year(db, academic_year)
    if not academic_year:
        return []

    query = _query_with_relations(db).join(
        TeacherAssignment, TeachingLog.assignment_id == TeacherAssignment.assignment_id
    ).filter(
        TeacherAssignment.teacher_id == teacher_id
    ).join(
        AcademicYear, TeacherAssignment.academic_id == AcademicYear.academic_id
    ).filter(AcademicYear.academic_year == academic_year)
    if from_date:
        query = query.filter(TeachingLog.teaching_date >= from_date)
    if to_date:
        query = query.filter(TeachingLog.teaching_date <= to_date)
    query = query.order_by(
        desc(TeachingLog.teaching_date),
        case((TeachingLog.status == ABSENT_STATUS, 1), else_=0).desc()
    )
    return query.all()


def get_by_id(db: Session, teaching_log_id: int) -> TeachingLog:
    obj = _query_with_relations(db).filter(
        TeachingLog.teaching_log_id == teaching_log_id
    ).first()
    if not obj:
        raise NotFoundException("ຂໍ້ມູນບັນທຶກການສອນ")
    return obj


def create(db: Session, data: TeachingLogCreate):
    _assert_assignment_in_active_year(db, data.assignment_id)
    if data.substitute_for_assignment_id:
        _assert_assignment_in_active_year(db, data.substitute_for_assignment_id)

    now = datetime.now()
    obj = TeachingLog(
        assignment_id=data.assignment_id,
        substitute_for_assignment_id=data.substitute_for_assignment_id,
        hourly=data.hourly,
        status=data.status or TEACHING_STATUS,
        teaching_date=now,
    )
    db.add(obj)
    db.flush()

    if data.substitute_for_assignment_id:
        sub_assignment = db.query(TeacherAssignment).filter(
            TeacherAssignment.assignment_id == data.substitute_for_assignment_id
        ).first()
        if sub_assignment:
            main_assignment = db.query(TeacherAssignment).filter(
                TeacherAssignment.assignment_id == data.assignment_id
            ).first()
            absent_log = TeachingLog(
                assignment_id=data.substitute_for_assignment_id,
                substitute_for_assignment_id=None,
                hourly=data.hourly,
                status=ABSENT_STATUS,
                teaching_date=now,
            )
            db.add(absent_log)

    db.commit()
    db.refresh(obj)
    return get_by_id(db, obj.teaching_log_id)


def update(db: Session, teaching_log_id: int, data: TeachingLogUpdate):
    obj = get_by_id(db, teaching_log_id)
    _assert_assignment_in_active_year(db, obj.assignment_id)
    if data.assignment_id and data.assignment_id != obj.assignment_id:
        _assert_assignment_in_active_year(db, data.assignment_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return get_by_id(db, teaching_log_id)


def delete(db: Session, teaching_log_id: int):
    obj = get_by_id(db, teaching_log_id)
    _assert_assignment_in_active_year(db, obj.assignment_id)
    db.delete(obj)
    db.commit()


def get_summary(db: Session, teacher_id: str = None, academic_year: str = None):
    """Get summary statistics efficiently using SQL aggregation."""
    from sqlalchemy import func

    academic_year = _resolve_academic_year(db, academic_year)
    if not academic_year:
        return {
            'total_count': 0,
            'taught_count': 0,
            'absent_count': 0,
            'total_hours': 0.0,
            'total_amount': 0.0,
        }

    query = db.query(
        func.count(TeachingLog.teaching_log_id).label('total_count'),
        func.sum(func.if_(TeachingLog.status == TEACHING_STATUS, 1, 0)).label('taught_count'),
        func.sum(func.if_(TeachingLog.status == ABSENT_STATUS, 1, 0)).label('absent_count'),
        func.sum(func.if_(TeachingLog.status == TEACHING_STATUS, TeachingLog.hourly, 0)).label('total_hours'),
        func.sum(
            func.if_(
                TeachingLog.status == TEACHING_STATUS,
                TeachingLog.hourly * TeacherAssignment.hourly_rate,
                0
            )
        ).label('total_amount')
    ).join(
        TeacherAssignment, TeachingLog.assignment_id == TeacherAssignment.assignment_id
    ).join(
        AcademicYear, TeacherAssignment.academic_id == AcademicYear.academic_id
    )

    query = query.filter(AcademicYear.academic_year == academic_year)

    if teacher_id:
        query = query.filter(TeacherAssignment.teacher_id == teacher_id)

    result = query.first()

    return {
        'total_count': result.total_count or 0,
        'taught_count': result.taught_count or 0,
        'absent_count': result.absent_count or 0,
        'total_hours': float(result.total_hours or 0),
        'total_amount': float(result.total_amount or 0),
    }
