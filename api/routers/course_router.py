"""
api/routers/course_router.py
Course endpoints dengan authentication & authorization.

Sesuai Chapter 7:
- Section 6: Protecting Endpoints (auth=apiAuth)
- Section 7.6: Authorization CRUD Course
"""
from typing import Optional, List
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from ninja import Router, Query
from ninja.errors import HttpError

from courses.models import Course, Category
from api.schemas import CourseOut, CourseIn, CourseUpdateSchema, MessageOut
from api.helpers import (
    get_authenticated_user,
    check_course_owner,
    check_owner_or_superadmin,
)

User = get_user_model()
router = Router(tags=['Courses'])


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS — tidak butuh token
# ─────────────────────────────────────────────────────────────

@router.get('', response=List[CourseOut])
def list_courses(
    request,
    page: int = Query(1),
    page_size: int = Query(10),
    search: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
):
    """
    List semua course yang published — PUBLIK, tidak butuh token.
    """
    from django.db.models import Count

    qs = Course.objects.filter(is_published=True).select_related(
        'instructor', 'category'
    )

    if search:
        qs = qs.filter(title__icontains=search)
    if level:
        qs = qs.filter(level=level)

    page_size = min(page_size, 50)
    offset = (page - 1) * page_size
    return list(qs[offset:offset + page_size])


@router.get('/{course_id}', response={200: CourseOut, 404: MessageOut})
def get_course(request, course_id: int):
    """Detail course — PUBLIK."""
    try:
        return Course.objects.select_related(
            'instructor', 'category'
        ).get(id=course_id, is_published=True)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")


# ─────────────────────────────────────────────────────────────
# PROTECTED ENDPOINTS — butuh token (auth=apiAuth)
# ─────────────────────────────────────────────────────────────

@router.post('', auth=True, response={201: CourseOut, 400: MessageOut, 403: MessageOut})
def create_course(request, data: CourseIn):
    """
    Buat course baru.

    Sesuai Chapter 7 Section 7.6:
    - Membutuhkan: Authorization: Bearer <access_token>
    - User yang membuat otomatis jadi instructor/owner course
    - Semua authenticated user bisa buat course (jadi instructor)

    request.user tersedia karena auth=True
    """
    # Ambil user dari token — sesuai Chapter 7 Section 6.2
    user = get_authenticated_user(request)

    # Generate slug unik dari title
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
        instructor=user,     # User yang membuat = instructor
        level=data.level,
        price=data.price,
        is_published=False,  # Default: draft
    )

    return 201, course


@router.put('/{course_id}', auth=True, response={200: CourseOut, 403: MessageOut, 404: MessageOut})
def update_course(request, course_id: int, data: CourseIn):
    """
    Update course.

    Sesuai Chapter 7 Section 7.6:
    Authorization: hanya course OWNER yang boleh edit.
    → HttpError(403) jika bukan owner.
    """
    user = get_authenticated_user(request)

    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    # Authorization check — sesuai Chapter 7 Section 7.6
    check_course_owner(course, user)  # Raise 403 otomatis jika bukan owner

    course.title = data.title
    course.description = data.description
    course.level = data.level
    course.price = data.price
    course.save()
    return course


@router.patch('/{course_id}', auth=True, response={200: CourseOut, 403: MessageOut, 404: MessageOut})
def partial_update_course(request, course_id: int, data: CourseUpdateSchema):
    """
    Update sebagian field course (partial update).
    Authorization: hanya owner atau superadmin.
    """
    user = get_authenticated_user(request)

    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    check_course_owner(course, user)

    if data.title is not None:
        course.title = data.title
    if data.description is not None:
        course.description = data.description
    if data.level is not None:
        course.level = data.level
    if data.price is not None:
        course.price = data.price
    if data.is_published is not None:
        course.is_published = data.is_published

    course.save()
    return course


@router.delete('/{course_id}', auth=True, response={200: MessageOut, 403: MessageOut, 404: MessageOut})
def delete_course(request, course_id: int):
    """
    Hapus course.

    Sesuai Chapter 7 Section 7.6:
    Authorization: course OWNER atau SUPERADMIN.
    → HttpError(403) jika tidak memenuhi keduanya.
    """
    user = get_authenticated_user(request)

    course = Course.objects.filter(id=course_id).first()
    if course is None:
        raise HttpError(404, "Course tidak ditemukan")

    # Authorization: owner ATAU superadmin — sesuai Chapter 7 Section 7.6
    check_owner_or_superadmin(course.instructor, user)

    title = course.title
    course.delete()
    return MessageOut(message=f"Course '{title}' berhasil dihapus")