"""
courses/managers.py
Custom QuerySet dan Manager untuk Simple LMS
"""
from django.db import models
from django.db.models import Count, Avg, Prefetch, Q


# ─────────────────────────────────────────────────────────────
# COURSE MANAGER
# ─────────────────────────────────────────────────────────────

class CourseQuerySet(models.QuerySet):
    """QuerySet kustom untuk model Course."""

    def published(self):
        """Hanya course yang sudah dipublikasikan."""
        return self.filter(is_published=True)

    def for_listing(self):
        """
        Query yang dioptimasi untuk tampilan list course.
        Sekaligus ambil data instructor dan category (select_related),
        serta hitung jumlah enrollment dan lesson (annotate).

        Tanpa ini: setiap akses course.instructor.name = query baru → N+1 problem.
        Dengan ini: semua data diambil sekaligus dalam 1 query JOIN.
        """
        return self.select_related(
            'instructor',    # ForeignKey → pakai select_related (JOIN)
            'category',      # ForeignKey → pakai select_related (JOIN)
        ).annotate(
            enrollment_count=Count('enrollments', distinct=True),
            lesson_count=Count('lessons', distinct=True),
        )

    def by_instructor(self, user):
        """Course yang diajar oleh user tertentu."""
        return self.filter(instructor=user)

    def with_full_details(self):
        """
        Query paling lengkap — untuk halaman detail course.
        Mengambil instructor, category, lessons, dan enrollments sekaligus.
        """
        return self.select_related(
            'instructor',
            'category',
            'category__parent',  # parent category sekalian
        ).prefetch_related(
            'lessons',           # Reverse FK → pakai prefetch_related
            Prefetch(
                'enrollments',
                queryset=__import__(
                    'courses.models', fromlist=['Enrollment']
                ).Enrollment.objects.select_related('student')
            )
        ).annotate(
            enrollment_count=Count('enrollments', distinct=True),
            lesson_count=Count('lessons', distinct=True),
            avg_progress=Avg('enrollments__progress_records__is_completed'),
        )


class CourseManager(models.Manager):
    """Manager kustom untuk Course yang menggunakan CourseQuerySet."""

    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)

    def published(self):
        return self.get_queryset().published()

    def for_listing(self):
        return self.get_queryset().for_listing()

    def by_instructor(self, user):
        return self.get_queryset().by_instructor(user)


# ─────────────────────────────────────────────────────────────
# ENROLLMENT MANAGER
# ─────────────────────────────────────────────────────────────

class EnrollmentQuerySet(models.QuerySet):
    """QuerySet kustom untuk model Enrollment."""

    def active(self):
        """Hanya enrollment yang masih aktif."""
        return self.filter(status='active')

    def for_student_dashboard(self, student):
        """
        Query dioptimasi untuk dashboard siswa.
        Mengambil semua enrollment + course + progress sekaligus.
        Mencegah N+1 problem saat render dashboard.

        Tanpa ini: untuk 10 enrollment → 10 query ke course + 10 query ke progress.
        Dengan ini: cukup 3 query total (enrollment + courses + progress).
        """
        return self.filter(
            student=student,
            status='active',
        ).select_related(
            'course',                  # ForeignKey → JOIN
            'course__instructor',      # Chain JOIN
            'course__category',        # Chain JOIN
        ).prefetch_related(
            Prefetch(
                'progress_records',    # Reverse FK → separate query
                queryset=__import__(
                    'courses.models', fromlist=['Progress']
                ).Progress.objects.select_related('lesson').order_by(
                    'lesson__order'
                ),
            )
        ).annotate(
            completed_lessons=Count(
                'progress_records',
                filter=Q(progress_records__is_completed=True),
            ),
            total_lessons=Count(
                'course__lessons',
                distinct=True,
            ),
        )

    def completed(self):
        """Hanya enrollment yang sudah selesai."""
        return self.filter(status='completed')


class EnrollmentManager(models.Manager):
    """Manager kustom untuk Enrollment."""

    def get_queryset(self):
        return EnrollmentQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_student_dashboard(self, student):
        return self.get_queryset().for_student_dashboard(student)

    def completed(self):
        return self.get_queryset().completed()