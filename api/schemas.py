"""
api/schemas.py
Pydantic Schemas untuk validasi input/output API Simple LMS.
Django Ninja menggunakan Pydantic untuk validasi otomatis.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, model_validator
import re


# ═══════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════════

class RegisterSchema(BaseModel):
    """Schema untuk POST /api/auth/register"""
    username: str
    email: EmailStr
    password: str
    password_confirm: str
    first_name: str = ''
    last_name: str = ''
    role: str = 'student'

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username minimal 3 karakter')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username hanya boleh huruf, angka, dan underscore')
        return v

    @field_validator('password')
    @classmethod
    def password_valid(cls, v):
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v

    @field_validator('role')
    @classmethod
    def role_valid(cls, v):
        allowed = ['student', 'instructor']
        if v not in allowed:
            raise ValueError(f'Role harus salah satu dari: {allowed}')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Password dan konfirmasi password tidak sama')
        return self


class LoginSchema(BaseModel):
    """Schema untuk POST /api/auth/login"""
    username: str
    password: str


class TokenSchema(BaseModel):
    """Schema response token JWT"""
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int   # detik


class RefreshTokenSchema(BaseModel):
    """Schema untuk POST /api/auth/refresh"""
    refresh_token: str


class UserOutSchema(BaseModel):
    """Schema response data user (tanpa password!)"""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    bio: str
    is_active: bool
    date_joined: datetime

    class Config:
        from_attributes = True   # Agar bisa dibuat dari Django model instance


class UpdateProfileSchema(BaseModel):
    """Schema untuk PUT /api/auth/me"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[EmailStr] = None


class ChangePasswordSchema(BaseModel):
    """Schema untuk ganti password"""
    old_password: str
    new_password: str
    new_password_confirm: str

    @model_validator(mode='after')
    def passwords_match(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError('Password baru dan konfirmasi tidak sama')
        return self


# ═══════════════════════════════════════════════════════════════
# CATEGORY SCHEMAS
# ═══════════════════════════════════════════════════════════════

class CategoryOutSchema(BaseModel):
    id: int
    name: str
    slug: str
    description: str

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# COURSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class InstructorBriefSchema(BaseModel):
    """Ringkasan instructor untuk ditampilkan di course"""
    id: int
    username: str
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class CourseOutSchema(BaseModel):
    """Schema response untuk daftar/detail course"""
    id: int
    title: str
    slug: str
    description: str
    level: str
    price: float
    is_published: bool
    instructor: InstructorBriefSchema
    category: Optional[CategoryOutSchema] = None
    total_lessons: int = 0
    total_enrollments: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CourseListSchema(BaseModel):
    """Schema response untuk list course dengan pagination"""
    items: List[CourseOutSchema]
    total: int
    page: int
    page_size: int
    total_pages: int


class CourseCreateSchema(BaseModel):
    """Schema untuk POST /api/courses (buat course baru)"""
    title: str
    description: str = ''
    category_id: Optional[int] = None
    level: str = 'beginner'
    price: float = 0.0

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Judul course tidak boleh kosong')
        return v.strip()

    @field_validator('level')
    @classmethod
    def level_valid(cls, v):
        allowed = ['beginner', 'intermediate', 'advanced']
        if v not in allowed:
            raise ValueError(f'Level harus salah satu dari: {allowed}')
        return v

    @field_validator('price')
    @classmethod
    def price_non_negative(cls, v):
        if v < 0:
            raise ValueError('Harga tidak boleh negatif')
        return v


class CourseUpdateSchema(BaseModel):
    """Schema untuk PATCH /api/courses/{id} (update sebagian field)"""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    level: Optional[str] = None
    price: Optional[float] = None
    is_published: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════
# LESSON SCHEMAS
# ═══════════════════════════════════════════════════════════════

class LessonOutSchema(BaseModel):
    id: int
    title: str
    content_type: str
    duration_minutes: int
    order: int
    is_free_preview: bool

    class Config:
        from_attributes = True


class CourseDetailSchema(CourseOutSchema):
    """Schema detail course — termasuk daftar lessons"""
    lessons: List[LessonOutSchema] = []


# ═══════════════════════════════════════════════════════════════
# ENROLLMENT SCHEMAS
# ═══════════════════════════════════════════════════════════════

class EnrollmentOutSchema(BaseModel):
    """Schema response enrollment"""
    id: int
    course: CourseOutSchema
    status: str
    enrolled_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnrollSchema(BaseModel):
    """Schema untuk POST /api/enrollments"""
    course_id: int


class ProgressUpdateSchema(BaseModel):
    """Schema untuk POST /api/enrollments/{id}/progress"""
    lesson_id: int
    is_completed: bool = True
    last_position_seconds: int = 0


class ProgressOutSchema(BaseModel):
    """Schema response progress"""
    lesson_id: int
    lesson_title: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    last_position_seconds: int

    class Config:
        from_attributes = True


class EnrollmentDetailSchema(BaseModel):
    """Schema detail enrollment — termasuk progress"""
    id: int
    course: CourseOutSchema
    status: str
    enrolled_at: datetime
    completed_at: Optional[datetime]
    progress: List[ProgressOutSchema] = []
    completed_lessons: int = 0
    total_lessons: int = 0
    completion_percentage: float = 0.0

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# GENERIC RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class MessageSchema(BaseModel):
    """Response generik untuk operasi yang berhasil"""
    message: str
    success: bool = True


class ErrorSchema(BaseModel):
    """Response untuk error"""
    message: str
    detail: Optional[str] = None
    success: bool = False