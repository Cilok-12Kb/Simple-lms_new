"""
api/routers/course_router.py
Endpoint Courses:
Public:
  GET  /api/courses          - List courses (pagination + filter)
  GET  /api/courses/{id}     - Detail course

Protected:
  POST   /api/courses        - Buat course baru (Instructor)
  PATCH  /api/courses/{id}   - Update course (Owner/Admin)
  DELETE /api/courses/{id}   - Hapus course (Admin only)
"""
from typing import Optional
from django.utils.text import slugify
from ninja import Router, Query
from ninja.errors import HttpError

from courses.models import Course, Category, Lesson
from api.schemas import (
    CourseOutSchema, CourseDetailSchema, CourseListSchema,
    CourseCreateSchema, CourseUpdateSchema, MessageSchema, ErrorSchema,
    LessonOutSchema
)
from api.auth import jwt_auth
from api.permissions import is_instructor, is_admin, is_course_owner

router = Router(tags=['Courses'])


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS (tidak butuh token)
# ─────────────────────────────────────────────────────────────

@router.get('', response=CourseListSchema)
def list_courses(
    request,
    page: int = Query(1, description="Nomor halaman (mulai dari 1)"),
    page_size: int = Query(10, description="Jumlah item per halaman (max 50)"),
    search: Optional[str] = Query(None, description="Cari berdasarkan judul course"),
    level: Optional[str] = Query(None, description="Filter: beginner/intermediate/advanced"),
    category_id: Optional[int] = Query(None, description="Filter berdasarkan ID kategori"),
    ordering: Optional[str] = Query('-created_at', description="Urutan: created_at, -created_at, price, -price, title"),
):
    """
    Ambil daftar course yang sudah dipublikasikan dengan pagination dan filter.
    
    Endpoint ini **tidak memerlukan token** — bisa diakses publik.
    """
    from django.db.models import Count

    # Validasi
    page_size = min(page_size, 50)   # Batasi max 50 per halaman
    if page < 1:
        page = 1

    # Base queryset — hanya yang published
    qs = Course.objects.filter(is_published=True).select_related(
        'instructor', 'category'
    ).annotate(
        total_enrollments_count=Count('enrollments', distinct=True),
        total_lessons_count=Count('lessons', distinct=True),
    )

    # Filter pencarian
    if search:
        qs = qs.filter(title__icontains=search)

    # Filter level
    if level:
        qs = qs.filter(level=level)

    # Filter kategori
    if category_id:
        qs = qs.filter(category_id=category_id)

    # Ordering
    allowed_orderings = ['created_at', '-created_at', 'price', '-price', 'title', '-title']
    if ordering in allowed_orderings:
        qs = qs.order_by(ordering)

    # Hitung total
    total = qs.count()
    total_pages = (total + page_size - 1) // page_size

    # Pagination
    offset = (page - 1) * page_size
    courses = qs[offset:offset + page_size]

    # Bangun response
    items = []
    for course in courses:
        items.append(CourseOutSchema(
            id=course.id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            level=course.level,
            price=float(course.price),
            is_published=course.is_published,
            instructor=course.instructor,
            category=course.category,
            total_lessons=course.total_lessons_count,
            total_enrollments=course.total_enrollments_count,
            created_at=course.created_at,
        ))

    return CourseListSchema(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get('/{course_id}', response={200: CourseDetailSchema, 404: ErrorSchema})
def get_course(request, course_id: int):
    """
    Ambil detail course beserta daftar lesson.
    
    Endpoint ini **tidak memerlukan token**.
    Lesson yang is_free_preview=True bisa diakses siapa saja.
    """
    try:
        course = Course.objects.select_related(
            'instructor', 'category'
        ).prefetch_related('lessons').get(id=course_id, is_published=True)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    lessons = [
        LessonOutSchema(
            id=l.id,
            title=l.title,
            content_type=l.content_type,
            duration_minutes=l.duration_minutes,
            order=l.order,
            is_free_preview=l.is_free_preview,
        )
        for l in course.lessons.all().order_by('order')
    ]

    return CourseDetailSchema(
        id=course.id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        level=course.level,
        price=float(course.price),
        is_published=course.is_published,
        instructor=course.instructor,
        category=course.category,
        total_lessons=course.lessons.count(),
        total_enrollments=course.enrollments.count(),
        created_at=course.created_at,
        lessons=lessons,
    )


# ─────────────────────────────────────────────────────────────
# PROTECTED ENDPOINTS (butuh token)
# ─────────────────────────────────────────────────────────────

@router.post('', auth=jwt_auth, response={201: CourseOutSchema, 400: ErrorSchema, 403: ErrorSchema})
@is_instructor
def create_course(request, data: CourseCreateSchema):
    """
    Buat course baru.
    
    **Membutuhkan role: instructor atau admin**
    
    Course yang baru dibuat statusnya `is_published=False` (draft).
    Instructor perlu mengubah ke published secara manual.
    """
    user = request.auth

    # Generate slug dari title
    base_slug = slugify(data.title)
    slug = base_slug
    counter = 1
    while Course.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Validasi category
    category = None
    if data.category_id:
        try:
            category = Category.objects.get(id=data.category_id)
        except Category.DoesNotExist:
            raise HttpError(400, f"Category dengan ID {data.category_id} tidak ditemukan")

    course = Course.objects.create(
        title=data.title,
        slug=slug,
        description=data.description,
        instructor=user,
        category=category,
        level=data.level,
        price=data.price,
        is_published=False,   # Default draft
    )

    return 201, CourseOutSchema(
        id=course.id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        level=course.level,
        price=float(course.price),
        is_published=course.is_published,
        instructor=course.instructor,
        category=course.category,
        total_lessons=0,
        total_enrollments=0,
        created_at=course.created_at,
    )


@router.patch('/{course_id}', auth=jwt_auth, response={200: CourseOutSchema, 403: ErrorSchema, 404: ErrorSchema})
@is_course_owner
def update_course(request, course_id: int, data: CourseUpdateSchema):
    """
    Update sebagian data course.
    
    **Membutuhkan: instructor pemilik course, atau admin**
    
    Hanya field yang dikirim yang akan diupdate.
    """
    try:
        course = Course.objects.select_related('instructor', 'category').get(id=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    update_fields = []

    if data.title is not None:
        course.title = data.title
        update_fields.append('title')
    if data.description is not None:
        course.description = data.description
        update_fields.append('description')
    if data.level is not None:
        course.level = data.level
        update_fields.append('level')
    if data.price is not None:
        course.price = data.price
        update_fields.append('price')
    if data.is_published is not None:
        course.is_published = data.is_published
        update_fields.append('is_published')
    if data.category_id is not None:
        try:
            course.category = Category.objects.get(id=data.category_id)
            update_fields.append('category')
        except Category.DoesNotExist:
            raise HttpError(400, "Category tidak ditemukan")

    if update_fields:
        course.save(update_fields=update_fields)

    return CourseOutSchema(
        id=course.id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        level=course.level,
        price=float(course.price),
        is_published=course.is_published,
        instructor=course.instructor,
        category=course.category,
        total_lessons=course.lessons.count(),
        total_enrollments=course.enrollments.count(),
        created_at=course.created_at,
    )


@router.delete('/{course_id}', auth=jwt_auth, response={200: MessageSchema, 403: ErrorSchema, 404: ErrorSchema})
@is_admin
def delete_course(request, course_id: int):
    """
    Hapus course beserta semua data terkait (lessons, enrollments, progress).
    
    **Membutuhkan role: admin**
    
    ⚠️ Operasi ini permanen dan tidak bisa dibatalkan!
    """
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    title = course.title
    course.delete()   # CASCADE akan hapus lessons, enrollments, progress

    return MessageSchema(message=f"Course '{title}' berhasil dihapus")