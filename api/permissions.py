"""
api/permissions.py
Role-Based Access Control (RBAC) untuk Simple LMS API.
Berisi decorator untuk membatasi akses berdasarkan role user.
"""
import functools
from typing import Callable
from ninja.errors import HttpError


def require_role(*roles):
    """
    Decorator generik untuk memeriksa role user.
    
    Penggunaan:
        @router.post("/create")
        @require_role('instructor', 'admin')
        def create_something(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if user is None:
                raise HttpError(401, "Authentication required")
            if user.role not in roles:
                raise HttpError(
                    403,
                    f"Akses ditolak. Role '{user.role}' tidak memiliki izin. "
                    f"Diperlukan: {list(roles)}"
                )
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def is_instructor(func: Callable) -> Callable:
    """
    Decorator: hanya instructor yang bisa akses.
    
    Penggunaan:
        @router.post("/courses")
        @is_instructor
        def create_course(request):
            ...
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if user is None:
            raise HttpError(401, "Authentication required")
        if user.role not in ('instructor', 'admin'):
            raise HttpError(403, "Hanya instructor yang dapat mengakses endpoint ini")
        return func(request, *args, **kwargs)
    return wrapper


def is_student(func: Callable) -> Callable:
    """Decorator: hanya student yang bisa akses."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if user is None:
            raise HttpError(401, "Authentication required")
        if user.role not in ('student', 'admin'):
            raise HttpError(403, "Hanya student yang dapat mengakses endpoint ini")
        return func(request, *args, **kwargs)
    return wrapper


def is_admin(func: Callable) -> Callable:
    """Decorator: hanya admin yang bisa akses."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if user is None:
            raise HttpError(401, "Authentication required")
        if user.role != 'admin':
            raise HttpError(403, "Hanya admin yang dapat mengakses endpoint ini")
        return func(request, *args, **kwargs)
    return wrapper


def is_course_owner(func: Callable) -> Callable:
    """
    Decorator: hanya instructor pemilik course atau admin yang bisa akses.
    Mengasumsikan ada parameter 'course_id' di fungsi.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        from courses.models import Course
        user = request.auth
        if user is None:
            raise HttpError(401, "Authentication required")

        # Admin bisa akses semua
        if user.role == 'admin':
            return func(request, *args, **kwargs)

        # Instructor hanya bisa akses course miliknya sendiri
        course_id = kwargs.get('course_id')
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                if course.instructor != user:
                    raise HttpError(403, "Kamu bukan pemilik course ini")
            except Course.DoesNotExist:
                raise HttpError(404, "Course tidak ditemukan")

        return func(request, *args, **kwargs)
    return wrapper