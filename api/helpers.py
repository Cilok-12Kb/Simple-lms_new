"""
api/helpers.py
Helper functions untuk authorization checks.

Sesuai Chapter 7 Section 7.7:
"Agar kode lebih bersih dan DRY (Don't Repeat Yourself),
buat helper function untuk pengecekan authorization yang sering digunakan."
"""
from django.contrib.auth import get_user_model
from ninja.errors import HttpError

User = get_user_model()


def get_authenticated_user(request):
    """
    Mendapatkan objek User lengkap dari request yang terautentikasi.

    Sesuai Chapter 7 Section 6.2:
    request.user diset oleh HttpJwtAuth setelah token valid.
    Kita query ulang ke DB untuk pastikan data terbaru.
    """
    return User.objects.get(pk=request.user.id)


def check_course_owner(course, user):
    """
    Memeriksa apakah user adalah pemilik (instructor) course.
    Raise HttpError(403) jika bukan owner.

    Sesuai Chapter 7 Section 7.6 & 7.7.
    Admin/superuser bisa bypass pengecekan ini.
    """
    if user.is_superuser:
        return  # Superadmin bisa akses semua

    if course.instructor != user:
        raise HttpError(403, "Hanya pemilik course yang dapat melakukan aksi ini")


def check_owner_or_superadmin(owner, user):
    """
    Memeriksa apakah user adalah pemilik resource atau superadmin.
    Raise HttpError(403) jika tidak memenuhi keduanya.

    Sesuai Chapter 7 Section 7.6:
    'Delete Course — hanya pemilik course dan superadmin yang boleh menghapus'
    """
    if user.is_superuser:
        return  # Superadmin bisa akses semua

    if owner != user:
        raise HttpError(403, "Anda tidak memiliki izin untuk melakukan aksi ini")


def check_enrollment(user, course):
    """
    Memeriksa apakah user terdaftar di course tertentu.
    Raise HttpError(403) jika tidak terdaftar.

    Sesuai Chapter 7 Section 7.3:
    'Hanya user yang terdaftar (enrolled) yang boleh memberikan komentar'
    """
    from courses.models import Enrollment
    if not Enrollment.objects.filter(student=user, course=course, status='active').exists():
        raise HttpError(403, "Anda tidak terdaftar di course ini")


def check_comment_permission(comment, user):
    """
    Memeriksa izin untuk edit/delete komentar.

    Sesuai Chapter 7 Section 7.4 & 7.5:
    - Edit: hanya pemilik komentar
    - Delete: pemilik komentar ATAU course owner ATAU superadmin
    """
    is_comment_owner = (comment.enrollment.student == user)
    is_superadmin = user.is_superuser

    return is_comment_owner or is_superadmin