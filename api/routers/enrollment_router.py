"""
api/routers/enrollment_router.py
Enrollment endpoints dengan authentication & authorization.

Sesuai Chapter 7:
- Section 6.3: Enroll ke Course
- Section 6.4: Get My Courses
- Section 7.3–7.5: Authorization checks
"""
from typing import List
from django.contrib.auth import get_user_model
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from courses.models import Course, Enrollment, Progress, Lesson
from api.schemas import (
    EnrollSchema, EnrollmentOut, ProgressUpdateSchema,
    ProgressOut, MessageOut,
)
from api.helpers import get_authenticated_user, check_enrollment
from celery.result import AsyncResult

User = get_user_model()
router = Router(tags=['Enrollments'])


@router.post('', auth=True, response={201: EnrollmentOut, 400: MessageOut})
def enroll_course(request, data: EnrollSchema):
    """
    Daftar ke course.
    Setelah enroll → trigger Celery task kirim email (async).
    """
    user = get_authenticated_user(request)

    if not user.is_student:
        raise HttpError(403, "Hanya student yang bisa mendaftar ke course")

    try:
        course = Course.objects.select_related('instructor', 'category').get(
            id=data.course_id, is_published=True
        )
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    if Enrollment.objects.filter(student=user, course=course).exists():
        raise HttpError(400, "Kamu sudah terdaftar di course ini")

    enrollment = Enrollment.objects.create(
        student=user, course=course, status='active'
    )

    # ── Trigger Tasks (async, user tidak perlu menunggu) ─────
    from api.tasks import send_enrollment_email, log_activity_task

    # Task 1: Kirim email di background
    send_enrollment_email.delay(user.id, course.id)

    # Task 2: Log aktivitas ke MongoDB
    log_activity_task.delay(
        user_id=user.id,
        action='enroll',
        course_name=course.title,
    )

    return 201, enrollment


@router.get('/my-courses', auth=True, response=List[EnrollmentOut])
def get_my_courses(request):
    """
    Daftar course yang saya ikuti.

    Sesuai Chapter 7 Section 6.4:
    - auth=True: hanya user yang login
    - select_related untuk hindari N+1 (sesuai materi Modul 5)
    """
    user = get_authenticated_user(request)

    # Sesuai Chapter 7 Section 6.4 — gunakan select_related
    my_enrollments = Enrollment.objects.filter(
        student=user
    ).select_related(
        'course__instructor',
        'course__category',
    )

    return list(my_enrollments)


@router.post('/{enrollment_id}/progress', auth=True, response={200: ProgressOut, 403: MessageOut, 404: MessageOut})
def update_progress(request, enrollment_id: int, data: ProgressUpdateSchema):
    """
    Tandai lesson sebagai selesai atau update posisi video.

    Authorization: hanya pemilik enrollment yang bisa update progress.
    """
    user = get_authenticated_user(request)

    # Cek enrollment milik user ini
    enrollment = Enrollment.objects.filter(id=enrollment_id, student=user).first()
    if enrollment is None:
        raise HttpError(404, "Enrollment tidak ditemukan")

    # Cek lesson ada di course ini
    lesson = Lesson.objects.filter(
        id=data.lesson_id, course=enrollment.course
    ).first()
    if lesson is None:
        raise HttpError(404, "Lesson tidak ditemukan di course ini")

    # Get or create progress
    progress, _ = Progress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={'is_completed': False, 'last_position_seconds': 0},
    )

    progress.last_position_seconds = data.last_position_seconds
    if data.is_completed and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()

    progress.save()

    return ProgressOut(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at,
        last_position_seconds=progress.last_position_seconds,
    )

@router.post('/{enrollment_id}/generate-certificate', auth=True, response={202: dict})
def request_certificate(request, enrollment_id: int):
    """
    Request generate sertifikat secara async.
    Response 202 Accepted — proses berjalan di background.
    """
    from api.tasks import generate_certificate
    user = get_authenticated_user(request)
    enrollment = Enrollment.objects.filter(id=enrollment_id, student=user).first()
    if enrollment is None:
        raise HttpError(404, "Enrollment tidak ditemukan")

    task = generate_certificate.delay(user.id, enrollment.course.id)
    return 202, {
        "task_id": task.id,
        "status": "processing",
        "message": "Sertifikat sedang digenerate. Cek status via /tasks/{task_id}/status/"
    }


@router.get('/tasks/{task_id}/status', auth=True, response=dict)
def check_task_status(request, task_id: str):
    """Cek status dan hasil Celery task."""
    result = AsyncResult(task_id)
    response = {"task_id": task_id, "status": result.status}
    if result.ready():
        response["result"] = result.result
    return response