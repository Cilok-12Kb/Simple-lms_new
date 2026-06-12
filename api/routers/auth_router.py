"""
api/routers/auth_router.py
Endpoint auth custom (register, profile).
Login & token refresh sudah dihandle mobile_auth_router dari ninja-simple-jwt.

Sesuai Chapter 7 Section 4: User Registration
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from ninja import Router
from ninja.errors import HttpError

from api.schemas import Register, UserOut, UserDetailOut, UpdateProfileSchema, MessageOut

User = get_user_model()

router = Router(tags=['User & Profile'])


@router.post('/register/', response={201: UserOut, 400: MessageOut})
def register(request, data: Register):
    """
    Daftarkan user baru.

    Sesuai Chapter 7 Section 4.2:
    - Cek duplikasi username dan email
    - Gunakan create_user() agar password di-hash otomatis
    - Response TIDAK menyertakan password
    """
    # Cek username sudah digunakan
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"Username '{data.username}' sudah digunakan")

    # Cek email sudah digunakan
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, f"Email '{data.email}' sudah terdaftar")

    # WAJIB: create_user() bukan create()!
    # create_user() otomatis hash password menggunakan PBKDF2+SHA256
    # create() akan simpan password sebagai plain text — BERBAHAYA!
    user = User.objects.create_user(
        username=data.username,
        password=data.password,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
    )

    return 201, user


@router.get('/me/', auth=True, response={200: UserDetailOut})
def get_me(request):
    """
    Ambil profil user yang sedang login.

    Membutuhkan: Authorization: Bearer <access_token>
    request.user diisi otomatis oleh ninja-simple-jwt setelah token divalidasi.
    """
    # request.user sudah diset oleh HttpJwtAuth — tidak perlu decode manual
    user = User.objects.get(pk=request.user.id)
    return user


@router.put('/me/', auth=True, response={200: UserDetailOut, 400: MessageOut})
def update_me(request, data: UpdateProfileSchema):
    """
    Update profil user yang sedang login.
    Hanya field yang dikirim yang diupdate (partial update).
    """
    user = User.objects.get(pk=request.user.id)

    update_fields = []
    if data.first_name is not None:
        user.first_name = data.first_name
        update_fields.append('first_name')
    if data.last_name is not None:
        user.last_name = data.last_name
        update_fields.append('last_name')
    if data.email is not None:
        if User.objects.filter(email=data.email).exclude(id=user.id).exists():
            raise HttpError(400, "Email sudah digunakan user lain")
        user.email = data.email
        update_fields.append('email')

    if update_fields:
        user.save(update_fields=update_fields)

    return user