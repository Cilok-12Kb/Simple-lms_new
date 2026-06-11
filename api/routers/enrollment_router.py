"""
api/routers/enrollment_router.py
Endpoint Enrollments:
- POST /api/enrollments                      - Daftar ke course (Student)
- GET  /api/enrollments/my-courses           - Daftar course saya
- POST /api/enrollments/{id}/progress        - Tandai lesson selesai
"""
from django.db import IntegrityError
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from courses.models import Course, Enrollment, Progress, Lesson
from api.schemas import (
    EnrollSchema, EnrollmentOutSchema, EnrollmentDetailSchema,
    ProgressUpdateSchema, ProgressOutSchema, MessageSchema, ErrorSchema
)
from api.auth import jwt_auth
from api.permissions import is_student

router = Router(tags=['Enrollments'])


@router.post('', auth=jwt_auth, response={201: EnrollmentOutSchema, 400: ErrorSchema, 403: ErrorSchema})
@is_student
def enroll_course(request, data: EnrollSchema):
    """
    Daftar ke course.
    
    **Membutuhkan role: student**
    
    Satu student hanya bisa mendaftar ke satu course satu kali
    (unique constraint di database akan mencegah duplikat).
    """
    user = request.auth

    # Cek course ada dan sudah published
    try:
        course = Course.objects.select_related('instructor', 'category').get(
            id=data.course_id,
            is_published=True
        )
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan atau belum dipublikasikan")

    # Cek sudah pernah enrollment
    if Enrollment.objects.filter(student=user, course=course).exists():
        raise HttpError(400, f"Kamu sudah terdaftar di course '{course.title}'")

    try:
        enrollment = Enrollment.objects.create(
            student=user,
            course=course,
            status='active',
        )
    except IntegrityError:
        raise HttpError(400, "Kamu sudah terdaftar di course ini")

    return 201, EnrollmentOutSchema(
        id=enrollment.id,
        course=CourseOutFromEnrollment(course),
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
        completed_at=enrollment.completed_at,
    )


def CourseOutFromEnrollment(course):
    """Helper untuk build CourseOutSchema dari course object."""
    from api.schemas import CourseOutSchema
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


@router.get('/my-courses', auth=jwt_auth, response=list[EnrollmentDetailSchema])
def my_courses(request):
    """
    Ambil semua course yang sudah saya daftarkan beserta progress belajar.
    
    **Membutuhkan token** (semua role bisa akses data miliknya sendiri)
    """
    from django.db.models import Count, Q

    user = request.auth

    enrollments = Enrollment.objects.filter(
        student=user
    ).select_related(
        'course__instructor',
        'course__category',
    ).prefetch_related(
        'progress_records__lesson',
    ).annotate(
        completed_count=Count(
            'progress_records',
            filter=Q(progress_records__is_completed=True)
        ),
        total_lessons_count=Count('course__lessons', distinct=True),
    )

    result = []
    for enrollment in enrollments:
        progress_list = []
        for p in enrollment.progress_records.all().order_by('lesson__order'):
            progress_list.append(ProgressOutSchema(
                lesson_id=p.lesson.id,
                lesson_title=p.lesson.title,
                is_completed=p.is_completed,
                completed_at=p.completed_at,
                last_position_seconds=p.last_position_seconds,
            ))

        total = enrollment.total_lessons_count
        completed = enrollment.completed_count
        pct = round((completed / total * 100), 1) if total > 0 else 0.0

        result.append(EnrollmentDetailSchema(
            id=enrollment.id,
            course=CourseOutFromEnrollment(enrollment.course),
            status=enrollment.status,
            enrolled_at=enrollment.enrolled_at,
            completed_at=enrollment.completed_at,
            progress=progress_list,
            completed_lessons=completed,
            total_lessons=total,
            completion_percentage=pct,
        ))

    return result


@router.post('/{enrollment_id}/progress', auth=jwt_auth, response={200: ProgressOutSchema, 400: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema})
def update_progress(request, enrollment_id: int, data: ProgressUpdateSchema):
    """
    Tandai lesson sebagai selesai atau update posisi video.
    
    **Membutuhkan token** — hanya pemilik enrollment yang bisa update.
    
    Body:
    - **lesson_id**: ID lesson yang ingin di-update
    - **is_completed**: true jika lesson sudah selesai
    - **last_position_seconds**: posisi terakhir video (untuk resume)
    """
    user = request.auth

    # Cek enrollment milik user ini
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id, student=user)
    except Enrollment.DoesNotExist:
        raise HttpError(404, "Enrollment tidak ditemukan")

    # Cek lesson ada dan milik course yang sama
    try:
        lesson = Lesson.objects.get(id=data.lesson_id, course=enrollment.course)
    except Lesson.DoesNotExist:
        raise HttpError(404, "Lesson tidak ditemukan di course ini")

    # Get or create progress record
    progress, created = Progress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={
            'is_completed': False,
            'last_position_seconds': 0,
        }
    )

    # Update progress
    update_fields = ['last_position_seconds']
    progress.last_position_seconds = data.last_position_seconds

    if data.is_completed and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        update_fields.extend(['is_completed', 'completed_at'])

    progress.save(update_fields=update_fields)

    # Cek apakah semua lesson sudah selesai → tandai enrollment completed
    total_lessons = enrollment.course.lessons.count()
    completed_lessons = enrollment.progress_records.filter(is_completed=True).count()

    if total_lessons > 0 and completed_lessons >= total_lessons:
        enrollment.mark_completed()

    return ProgressOutSchema(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        last_position_seconds=progress.last_position_seconds,
    )