"""
api/routers/auth_router.py
Endpoint Authentication:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/refresh
- GET  /api/auth/me
- PUT  /api/auth/me
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password
from ninja import Router
from ninja.errors import HttpError

from api.schemas import (
    RegisterSchema, LoginSchema, TokenSchema,
    RefreshTokenSchema, UserOutSchema, UpdateProfileSchema,
    MessageSchema, ErrorSchema
)
from api.auth import create_token_pair, decode_token, jwt_auth

User = get_user_model()

# Router dengan prefix '/auth'
router = Router(tags=['Authentication'])


@router.post('/register', response={201: UserOutSchema, 400: ErrorSchema})
def register(request, data: RegisterSchema):
    """
    Daftarkan user baru.
    
    - **username**: unik, min 3 karakter, hanya huruf/angka/underscore
    - **email**: format email valid
    - **password**: min 8 karakter
    - **role**: 'student' atau 'instructor' (default: student)
    """
    # Cek username sudah ada
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"Username '{data.username}' sudah digunakan")

    # Cek email sudah ada
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, f"Email '{data.email}' sudah terdaftar")

    # Buat user baru
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),   # Hash password!
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        is_active=True,
    )

    return 201, user


@router.post('/login', response={200: TokenSchema, 401: ErrorSchema})
def login(request, data: LoginSchema):
    """
    Login dan dapatkan JWT tokens.
    
    Response berisi:
    - **access_token**: dipakai untuk request ke endpoint protected (expires 1 jam)
    - **refresh_token**: dipakai untuk minta access_token baru (expires 7 hari)
    
    Gunakan token di header: `Authorization: Bearer <access_token>`
    """
    # Cari user berdasarkan username
    try:
        user = User.objects.get(username=data.username)
    except User.DoesNotExist:
        raise HttpError(401, "Username atau password salah")

    # Verifikasi password
    if not check_password(data.password, user.password):
        raise HttpError(401, "Username atau password salah")

    # Cek user aktif
    if not user.is_active:
        raise HttpError(401, "Akun tidak aktif. Hubungi administrator.")

    # Buat dan return token pair
    tokens = create_token_pair(user)
    return 200, tokens


@router.post('/refresh', response={200: TokenSchema, 401: ErrorSchema})
def refresh_token(request, data: RefreshTokenSchema):
    """
    Minta access token baru menggunakan refresh token.
    
    Gunakan ini ketika access_token sudah expired (1 jam).
    Refresh token berlaku selama 7 hari.
    """
    payload = decode_token(data.refresh_token)

    if payload is None:
        raise HttpError(401, "Refresh token tidak valid atau sudah expired")

    if payload.get('type') != 'refresh':
        raise HttpError(401, "Token yang diberikan bukan refresh token")

    try:
        user = User.objects.get(id=payload['user_id'], is_active=True)
    except User.DoesNotExist:
        raise HttpError(401, "User tidak ditemukan atau tidak aktif")

    tokens = create_token_pair(user)
    return 200, tokens


@router.get('/me', auth=jwt_auth, response={200: UserOutSchema})
def get_me(request):
    """
    Ambil data profil user yang sedang login.
    
    Membutuhkan: `Authorization: Bearer <access_token>`
    """
    return request.auth


@router.put('/me', auth=jwt_auth, response={200: UserOutSchema, 400: ErrorSchema})
def update_me(request, data: UpdateProfileSchema):
    """
    Update profil user yang sedang login.
    Hanya field yang dikirim yang akan diupdate (partial update).
    """
    user = request.auth

    # Update hanya field yang dikirim (tidak None)
    update_fields = []
    if data.first_name is not None:
        user.first_name = data.first_name
        update_fields.append('first_name')
    if data.last_name is not None:
        user.last_name = data.last_name
        update_fields.append('last_name')
    if data.bio is not None:
        user.bio = data.bio
        update_fields.append('bio')
    if data.email is not None:
        # Cek email belum dipakai user lain
        if User.objects.filter(email=data.email).exclude(id=user.id).exists():
            raise HttpError(400, "Email sudah digunakan user lain")
        user.email = data.email
        update_fields.append('email')

    if update_fields:
        user.save(update_fields=update_fields)

    return user