"""
api/routers/course_router.py
Course endpoints dengan Redis Caching (Chapter 11 Cache-Aside Pattern).
"""
from typing import Optional, List
from django.core.cache import cache, caches
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle

from courses.models import Course, Category
from api.schemas import CourseOut, CourseIn, CourseUpdateSchema, MessageOut
from api.helpers import get_authenticated_user, check_course_owner, check_owner_or_superadmin

User = get_user_model()
router = Router(tags=['Courses'])

# TTL cache untuk course
COURSE_LIST_TTL = 300   # 5 menit
COURSE_DETAIL_TTL = 300  # 5 menit


# ─────────────────────────────────────────────────────────────
# RATE LIMITING — 60 req/menit, tersimpan di Redis
# Sesuai requirement: Rate limiting (60 requests/minute)
# ─────────────────────────────────────────────────────────────


@router.get('', response=List[CourseOut])
def list_courses(
    request,
    page: int = Query(1),
    page_size: int = Query(10),
    search: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    ordering: str = Query('-created_at'),
):
    """
    List course dengan Cache-Aside Pattern (sesuai Chapter 11 Section 7.1).

    Cache key unik berdasarkan semua parameter filter,
    agar tiap kombinasi filter punya cache sendiri.
    """
    from django.db.models import Count

    # Buat cache key yang mencerminkan semua parameter
    cache_key = f"course_list:p{page}:ps{page_size}:s{search}:l{level}:o{ordering}"

    # ── 1. Cek cache ──────────────────────────────────────────
    cached = cache.get(cache_key)
    if cached is not None:
        return cached  # Cache HIT — langsung return

    # ── 2. Cache MISS — query database ───────────────────────
    page_size = min(page_size, 50)
    qs = Course.objects.filter(is_published=True).select_related(
        'instructor', 'category'
    )
    if search:
        qs = qs.filter(title__icontains=search)
    if level:
        qs = qs.filter(level=level)

    allowed_orderings = ['created_at', '-created_at', 'price', '-price', 'title', '-title']
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)

    offset = (page - 1) * page_size
    courses = list(qs[offset:offset + page_size])

    # ── 3. Simpan ke cache ───────────────────────────────────
    cache.set(cache_key, courses, timeout=COURSE_LIST_TTL)
    return courses


@router.get('/{course_id}', response={200: CourseOut, 404: MessageOut})
def get_course(request, course_id: int):
    """
    Detail course dengan Cache-Aside Pattern.
    Cache key: 'course_detail:{id}'
    """
    cache_key = f"course_detail:{course_id}"

    # ── 1. Cek cache ──────────────────────────────────────────
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # ── 2. Cache MISS ─────────────────────────────────────────
    try:
        course = Course.objects.select_related(
            'instructor', 'category'
        ).get(id=course_id, is_published=True)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    # ── 3. Simpan ke cache ───────────────────────────────────
    cache.set(cache_key, course, timeout=COURSE_DETAIL_TTL)
    return course


@router.post('', auth=True, response={201: CourseOut, 400: MessageOut})
def create_course(request, data: CourseIn):
    """Buat course baru + invalidasi cache list."""
    user = get_authenticated_user(request)

    base_slug = slugify(data.title)
    slug = base_slug
    counter = 1
    while Course.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    course = Course.objects.create(
        title=data.title,
        slug=slug,
        description=data.description,
        instructor=user,
        level=data.level,
        price=data.price,
        is_published=False,
    )

    # ── Write-Through: Invalidasi cache list (Chapter 11 Section 7.2) ──
    # Hapus semua cache course_list karena ada data baru
    from django_redis import get_redis_connection
    redis_conn = get_redis_connection("default")
    keys = redis_conn.keys("*course_list*")
    if keys:
        redis_conn.delete(*keys)

    # Trigger Celery task: log activity ke MongoDB
    from api.tasks import log_activity_task
    log_activity_task.delay(
        user_id=user.id,
        action='create_course',
        course_name=course.title,
    )

    return 201, course


@router.put('/{course_id}', auth=True, response={200: CourseOut, 403: MessageOut, 404: MessageOut})
def update_course(request, course_id: int, data: CourseIn):
    """Update course + invalidasi cache."""
    user = get_authenticated_user(request)
    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    check_course_owner(course, user)

    course.title = data.title
    course.description = data.description
    course.level = data.level
    course.price = data.price
    course.save()

    # Invalidasi cache list DAN detail
    from django_redis import get_redis_connection
    redis_conn = get_redis_connection("default")
    keys = redis_conn.keys("*course_list*")
    if keys:
        redis_conn.delete(*keys)
    cache.delete(f"course_detail:{course_id}")

    return course


@router.delete('/{course_id}', auth=True, response={200: MessageOut, 403: MessageOut, 404: MessageOut})
def delete_course(request, course_id: int):
    """Hapus course + invalidasi cache."""
    user = get_authenticated_user(request)
    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    check_owner_or_superadmin(course.instructor, user)
    title = course.title
    course.delete()

    # Invalidasi semua cache terkait
    from django_redis import get_redis_connection
    redis_conn = get_redis_connection("default")
    keys = redis_conn.keys("*course_list*")
    if keys:
        redis_conn.delete(*keys)
    cache.delete(f"course_detail:{course_id}")

    return MessageOut(message=f"Course '{title}' berhasil dihapus")


@router.post('/{course_id}/export-report', auth=True, response={202: dict})
def export_report(request, course_id: int):
    """
    Generate laporan CSV course secara async (Task 4).
    """
    from api.tasks import export_course_report
    user = get_authenticated_user(request)
    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    check_course_owner(course, user)

    task = export_course_report.delay(course_id, user.id)
    return 202, {
        "task_id": task.id,
        "status": "processing",
        "message": "Laporan sedang digenerate. Cek status via /enrollments/tasks/{task_id}/status/"
    }