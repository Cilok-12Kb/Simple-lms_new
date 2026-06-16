"""
api/routers/analytics_router.py
Endpoint analytics menggunakan MongoDB.
"""
from typing import Optional
from ninja import Router, Schema
from api.mongodb_service import (
    log_activity, get_user_activity,
    get_popular_courses, get_daily_summary
)

router = Router(tags=['Analytics'])


class LogActivityIn(Schema):
    action: str
    course_name: Optional[str] = None
    metadata: Optional[dict] = None


@router.post('/log/', auth=True, response={201: dict})
def log_user_activity(request, data: LogActivityIn):
    """Catat aktivitas user ke MongoDB."""
    from api.helpers import get_authenticated_user
    user = get_authenticated_user(request)
    log_id = log_activity(
        user_id=user.id,
        action=data.action,
        course_name=data.course_name,
        metadata=data.metadata,
    )
    return 201, {"log_id": log_id, "status": "logged"}


@router.get('/my-activity/', auth=True, response=list)
def my_activity(request):
    """Aktivitas saya (10 terbaru)."""
    from api.helpers import get_authenticated_user
    user = get_authenticated_user(request)
    return get_user_activity(user.id)


@router.get('/popular-courses/', response=list)
def popular_courses(request, limit: int = 5):
    """Top course terpopuler berdasarkan views."""
    return get_popular_courses(limit=limit)


@router.get('/daily-summary/', response=list)
def daily_summary(request, days: int = 7):
    """Ringkasan aktivitas harian."""
    return get_daily_summary(days=days)