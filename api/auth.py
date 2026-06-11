"""
api/auth.py
JWT Token utilities dan Django Ninja Authentication class.
"""
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer

User = get_user_model()


# ─────────────────────────────────────────────────────────────
# TOKEN GENERATION
# ─────────────────────────────────────────────────────────────

def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    Buat JWT access token.
    Payload berisi: user_id, username, role, exp (expiry), type.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'access',
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """
    Buat JWT refresh token.
    Hanya berisi user_id dan expiry — lebih minimal dari access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        'user_id': user_id,
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'type': 'refresh',
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode dan validasi JWT token.
    Return payload jika valid, None jika tidak valid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None   # Token sudah expired
    except jwt.InvalidTokenError:
        return None   # Token tidak valid (dimanipulasi, format salah, dll)


def create_token_pair(user) -> Dict[str, Any]:
    """
    Buat pasangan access + refresh token untuk satu user.
    Dipakai saat login dan refresh.
    """
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    refresh_token = create_refresh_token(user_id=user.id)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer',
        'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ─────────────────────────────────────────────────────────────
# DJANGO NINJA AUTH CLASS
# ─────────────────────────────────────────────────────────────

class JWTAuth(HttpBearer):
    """
    Django Ninja Authentication class.
    
    Cara kerja:
    1. Client kirim header: Authorization: Bearer <access_token>
    2. Django Ninja otomatis memanggil authenticate()
    3. Kita decode token dan return user object
    4. Jika return None → 401 Unauthorized otomatis
    5. Jika return user → user tersedia di request.auth
    
    Penggunaan di endpoint:
        @router.get("/protected", auth=JWTAuth())
        def protected_endpoint(request):
            user = request.auth   # ← user yang sudah terautentikasi
    """

    def authenticate(self, request, token: str):
        payload = decode_token(token)
        if payload is None:
            return None   # Token tidak valid → 401

        if payload.get('type') != 'access':
            return None   # Ini refresh token, bukan access token

        user_id = payload.get('user_id')
        if not user_id:
            return None

        try:
            user = User.objects.get(id=user_id, is_active=True)
            return user
        except User.DoesNotExist:
            return None


# Instance yang akan dipakai di seluruh router
jwt_auth = JWTAuth()


# ─────────────────────────────────────────────────────────────
# OPTIONAL AUTH (untuk endpoint publik yang bisa login/anonim)
# ─────────────────────────────────────────────────────────────

class OptionalJWTAuth(HttpBearer):
    """
    Auth opsional — tidak wajib token.
    Jika ada token yang valid, user tersedia.
    Jika tidak ada/invalid, request.auth = None (bukan 401).
    """
    openapi_scheme = 'bearer'

    def authenticate(self, request, token: str):
        if not token:
            return None
        payload = decode_token(token)
        if not payload or payload.get('type') != 'access':
            return None
        try:
            return User.objects.get(id=payload['user_id'], is_active=True)
        except User.DoesNotExist:
            return None


optional_jwt_auth = OptionalJWTAuth()