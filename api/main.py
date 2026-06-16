"""
api/main.py
NinjaAPI instance menggunakan ninja-simple-jwt untuk authentication.
Sesuai Chapter 7: Authentication & Authorization.
"""
from ninja import NinjaAPI
from ninja.errors import HttpError, ValidationError
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

from api.routers.course_router import router as course_router
from api.routers.enrollment_router import router as enrollment_router
from api.routers.auth_router import router as auth_router
from api.routers.analytics_router import router as analytics_router

# ─────────────────────────────────────────────────────────────
# RATE LIMITING (Chapter 9 Section 5.4)
# ─────────────────────────────────────────────────────────────
from django.core.cache import caches

class AnonThrottle(AnonRateThrottle):
    def __init__(self):
        super().__init__(rate="60/minute")

class AuthThrottle(AuthRateThrottle):
    def __init__(self):
        super().__init__(rate="60/minute")

# ─────────────────────────────────────────────────────────────
# INISIALISASI NINJA API
# ─────────────────────────────────────────────────────────────
apiv1 = NinjaAPI(
    title='Simple LMS API',
    version='1.0.0',
    description='''
## Simple LMS REST API

### Authentication
1. Register: `POST /api/register/`
2. Login: `POST /api/auth/sign-in` → dapat `access` token
3. Gunakan di header: `Authorization: Bearer <access_token>`
4. Token expired: `POST /api/auth/token-refresh`

### Role & Permission
| Role | Hak Akses |
|------|-----------|
| **student** | Lihat course, enroll, update progress |
| **instructor** | + Buat & edit course milik sendiri |
| **admin/superuser** | Semua akses + hapus course manapun |
    ''',
    docs_url='/docs',
    openapi_url='/openapi.json',
    throttle=[AnonThrottle(), AuthThrottle()],
)

# ─────────────────────────────────────────────────────────────
# JWT AUTH HANDLER
# ─────────────────────────────────────────────────────────────
apiAuth = HttpJwtAuth()

# ─────────────────────────────────────────────────────────────
# REGISTER ROUTERS
# ─────────────────────────────────────────────────────────────
apiv1.add_router('/auth/', mobile_auth_router)
apiv1.add_router('/courses/', course_router)
apiv1.add_router('/enrollments/', enrollment_router)
apiv1.add_router('/', auth_router)
apiv1.add_router('/analytics/', analytics_router)  # ← dipindah ke sini

# ─────────────────────────────────────────────────────────────
# CUSTOM ERROR HANDLERS
# ─────────────────────────────────────────────────────────────
@apiv1.exception_handler(HttpError)
def http_error_handler(request, exc):
    return apiv1.create_response(
        request,
        {'message': str(exc.message), 'success': False},
        status=exc.status_code,
    )

@apiv1.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    return apiv1.create_response(
        request,
        {'message': 'Validasi gagal', 'detail': exc.errors, 'success': False},
        status=422,
    )