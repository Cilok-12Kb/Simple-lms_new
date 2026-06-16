"""
api/tasks.py
Celery tasks untuk Simple LMS.
Sesuai Chapter 13 & Requirement Progres 4:
  1. send_enrollment_email     - email saat enroll
  2. generate_certificate      - certificate saat course selesai
  3. update_course_statistics  - update statistik (scheduled)
  4. export_course_report      - generate CSV report (async)
"""
from celery import shared_task
from datetime import datetime
import csv
import io


# ─────────────────────────────────────────────────────────────
# TASK 1: Send Enrollment Email
# ─────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='api.tasks.send_enrollment_email'
)
def send_enrollment_email(self, user_id: int, course_id: int):
    """
    Kirim email konfirmasi enrollment ke student.

    Dipanggil saat student berhasil enroll ke course.
    Dijalankan di background — user tidak perlu menunggu email terkirim.

    Sesuai Chapter 13 Section 6.1: Asynchronous email notification.
    """
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Course

        User = get_user_model()
        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)

        # Di production: gunakan django.core.mail.send_mail()
        # Untuk demo: simulasi dengan print
        print(f"""
        ==========================================
        [EMAIL] Konfirmasi Enrollment
        ==========================================
        Kepada: {user.email}
        Subject: Berhasil Mendaftar di {course.title}

        Halo {user.get_full_name() or user.username},

        Selamat! Anda berhasil mendaftar di course:
        Judul: {course.title}
        Level: {course.get_level_display()}
        Harga: Rp {course.price:,.0f}

        Silakan akses dashboard untuk memulai belajar.

        Salam,
        Tim Simple LMS
        ==========================================
        Dikirim pada: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """)

        # Log aktivitas ke MongoDB
        from api.mongodb_service import log_activity
        log_activity(
            user_id=user_id,
            action='enrollment_email_sent',
            course_name=course.title,
            metadata={'email': user.email, 'task_id': self.request.id}
        )

        return {
            "status": "sent",
            "to": user.email,
            "course": course.title,
        }

    except Exception as exc:
        print(f"[EMAIL ERROR] Retry {self.request.retries}: {exc}")
        self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────
# TASK 2: Generate Certificate
# ─────────────────────────────────────────────────────────────

@shared_task(
    name='api.tasks.generate_certificate',
    max_retries=2,
)
def generate_certificate(user_id: int, course_id: int):
    """
    Generate sertifikat penyelesaian course.

    Dipanggil saat student menyelesaikan semua lesson di course.
    Sesuai Progres 4 requirement: generate certificate.
    """
    from django.contrib.auth import get_user_model
    from courses.models import Course, Enrollment, Progress

    User = get_user_model()
    user = User.objects.get(pk=user_id)
    course = Course.objects.get(pk=course_id)

    # Verifikasi semua lesson sudah selesai
    try:
        enrollment = Enrollment.objects.get(student=user, course=course)
    except Enrollment.DoesNotExist:
        return {"status": "error", "message": "Enrollment tidak ditemukan"}

    total_lessons = course.lessons.count()
    completed = Progress.objects.filter(
        enrollment=enrollment,
        is_completed=True
    ).count()

    if completed < total_lessons:
        return {
            "status": "incomplete",
            "message": f"Baru {completed}/{total_lessons} lesson selesai",
        }

    # Generate certificate (simulasi)
    cert_data = {
        "certificate_id": f"CERT-{user_id}-{course_id}-{datetime.now().strftime('%Y%m%d')}",
        "student_name": user.get_full_name() or user.username,
        "course_title": course.title,
        "completion_date": datetime.now().strftime('%d %B %Y'),
        "issued_by": "Simple LMS - Universitas Dian Nuswantoro",
    }

    print(f"""
    ==========================================
    [CERTIFICATE] Sertifikat Penyelesaian
    ==========================================
    ID       : {cert_data['certificate_id']}
    Nama     : {cert_data['student_name']}
    Course   : {cert_data['course_title']}
    Tanggal  : {cert_data['completion_date']}
    Penerbit : {cert_data['issued_by']}
    ==========================================
    """)

    # Simpan ke MongoDB sebagai record
    from api.mongodb_service import get_db
    db = get_db()
    db.certificates.insert_one({**cert_data, "user_id": user_id, "course_id": course_id})

    return cert_data


# ─────────────────────────────────────────────────────────────
# TASK 3: Update Course Statistics (Scheduled)
# ─────────────────────────────────────────────────────────────

@shared_task(name='api.tasks.update_course_statistics')
def update_course_statistics():
    from courses.models import Course, Enrollment, Lesson
    from django.db.models import Count, Avg
    from api.mongodb_service import save_course_statistics

    print(f"[STATS] Updating course statistics — {datetime.now()}")

    stats = Course.objects.annotate(
        enrollment_count=Count('enrollments', distinct=True),
        lesson_count=Count('lessons', distinct=True),
    ).values(
        'id', 'title', 'level', 'price',
        'enrollment_count', 'lesson_count', 'is_published'
    )

    # ── Konversi Decimal ke float agar bisa disimpan ke MongoDB ──
    courses_list = []
    for course in stats:
        course['price'] = float(course['price']) if course['price'] else 0.0
        courses_list.append(course)

    all_stats = {
        "generated_at": datetime.now().isoformat(),
        "total_courses": Course.objects.count(),
        "total_enrollments": Enrollment.objects.count(),
        "courses": courses_list,  # ← pakai courses_list
    }

    doc_id = save_course_statistics(all_stats)
    print(f"[STATS] Statistik disimpan ke MongoDB — ID: {doc_id}")

    return {
        "status": "updated",
        "total_courses": all_stats["total_courses"],
        "mongo_id": doc_id,
    }


# ─────────────────────────────────────────────────────────────
# TASK 4: Export Course Report (Async CSV)
# ─────────────────────────────────────────────────────────────

@shared_task(name='api.tasks.export_course_report')
def export_course_report(course_id: int, requested_by_id: int):
    """
    Generate laporan CSV untuk sebuah course secara async.

    Sesuai Progres 4 requirement: export_course_report.
    Sesuai Chapter 13 Section 6.2: Generate report async.
    """
    from courses.models import Course, Enrollment, Lesson
    from django.db.models import Count

    course = Course.objects.select_related('instructor').get(pk=course_id)
    enrollments = Enrollment.objects.filter(course=course).select_related('student')

    # Generate CSV di memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'No', 'Student Username', 'Student Email',
        'Status', 'Enrolled At', 'Completed At'
    ])

    # Data rows
    for i, enrollment in enumerate(enrollments, 1):
        writer.writerow([
            i,
            enrollment.student.username,
            enrollment.student.email,
            enrollment.status,
            enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M'),
            enrollment.completed_at.strftime('%Y-%m-%d %H:%M') if enrollment.completed_at else '-',
        ])

    csv_content = output.getvalue()

    # Di production: simpan ke S3/storage dan kirim link download via email
    # Untuk demo: simpan ringkasan ke MongoDB
    from api.mongodb_service import get_db
    db = get_db()
    report_doc = {
        "type": "csv_export",
        "course_id": course_id,
        "course_title": course.title,
        "requested_by": requested_by_id,
        "generated_at": datetime.now(),
        "row_count": enrollments.count(),
        "csv_preview": csv_content[:500],  # Preview 500 char pertama
    }
    db.reports.insert_one(report_doc)

    print(f"[REPORT] CSV untuk '{course.title}' selesai ({enrollments.count()} rows)")

    return {
        "status": "completed",
        "course": course.title,
        "total_rows": enrollments.count(),
        "csv_content": csv_content,  # Hasil tersedia via AsyncResult
    }


# ─────────────────────────────────────────────────────────────
# UTILITY TASK: Log Activity (dipanggil dari berbagai endpoint)
# ─────────────────────────────────────────────────────────────

@shared_task(name='api.tasks.log_activity_task')
def log_activity_task(user_id: int, action: str, course_name: str = None,
                      metadata: dict = None):
    """Helper task untuk log aktivitas ke MongoDB secara async."""
    from api.mongodb_service import log_activity
    log_id = log_activity(
        user_id=user_id,
        action=action,
        course_name=course_name,
        metadata=metadata,
    )
    return {"log_id": log_id}