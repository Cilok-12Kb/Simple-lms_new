"""
api/main.py
NinjaAPI instance utama — titik masuk seluruh REST API.
"""
from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError
from django.http import JsonResponse

from api.routers.auth_router import router as auth_router
from api.routers.course_router import router as course_router
from api.routers.enrollment_router import router as enrollment_router

# ─────────────────────────────────────────────────────────────
# BUAT NINJA API INSTANCE
# ─────────────────────────────────────────────────────────────
api = NinjaAPI(
    title='Simple LMS API',
    version='1.0.0',
    description='''
## Simple LMS REST API

API untuk sistem manajemen pembelajaran sederhana.

### Authentication
API ini menggunakan **JWT Bearer Token**.

1. Daftar akun: `POST /api/auth/register`
2. Login: `POST /api/auth/login` → dapat `access_token`
3. Gunakan token di header: `Authorization: Bearer <access_token>`
4. Jika token expired: `POST /api/auth/refresh`

### Role & Permission
| Role | Bisa Akses |
|------|-----------|
| **student** | Lihat course, enroll, update progress |
| **instructor** | + Buat & edit course milik sendiri |
| **admin** | Semua akses + hapus course |
    ''',
    docs_url='/docs',      # Swagger UI di /api/docs
    openapi_url='/openapi.json',
)


# ─────────────────────────────────────────────────────────────
# REGISTER ROUTERS
# ─────────────────────────────────────────────────────────────
api.add_router('/auth',        auth_router)
api.add_router('/courses',     course_router)
api.add_router('/enrollments', enrollment_router)


# ─────────────────────────────────────────────────────────────
# CUSTOM ERROR HANDLERS
# ─────────────────────────────────────────────────────────────
@api.exception_handler(HttpError)
def http_error_handler(request, exc):
    return api.create_response(
        request,
        {'message': str(exc.message), 'success': False},
        status=exc.status_code,
    )


@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    return api.create_response(
        request,
        {'message': 'Validasi gagal', 'detail': exc.errors, 'success': False},
        status=422,
    )