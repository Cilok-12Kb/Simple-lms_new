"""
api/schemas.py
Pydantic Schemas untuk Simple LMS API.
Sesuai Chapter 7: Registration, User, Course, Enrollment, Comment.
"""
from datetime import datetime
from typing import Optional, List
from ninja import Schema
from pydantic import field_validator, model_validator, EmailStr
import re


# ═══════════════════════════════════════════════════════════════
# USER / AUTH SCHEMAS
# ═══════════════════════════════════════════════════════════════

class Register(Schema):
    """
    Schema untuk POST /api/register/
    Sesuai Chapter 7 Section 4.1
    """
    username: str
    password: str
    password_confirm: str
    email: EmailStr
    first_name: str
    last_name: str

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username minimal 3 karakter')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username hanya boleh huruf, angka, underscore')
        return v

    @field_validator('password')
    @classmethod
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password minimal 8 karakter')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Password dan konfirmasi tidak sama')
        return self


class UserOut(Schema):
    """
    Schema response data user — TANPA password!
    Sesuai Chapter 7 Section 4.1
    """
    id: int
    username: str
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class UserDetailOut(Schema):
    """Schema detail user dengan role dan bio."""
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    is_active: bool
    date_joined: datetime

    class Config:
        from_attributes = True


class UpdateProfileSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


# ═══════════════════════════════════════════════════════════════
# COURSE SCHEMAS
# ═══════════════════════════════════════════════════════════════

class CourseIn(Schema):
    """
    Schema input untuk buat/update course.
    Sesuai Chapter 7 Section 7.6
    """
    title: str
    description: str = ''
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
        if v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Level harus: beginner, intermediate, atau advanced')
        return v


class CourseOut(Schema):
    """Schema response course."""
    id: int
    title: str
    slug: str
    description: str
    level: str
    price: float
    is_published: bool
    instructor: UserOut
    created_at: datetime

    class Config:
        from_attributes = True


class CourseUpdateSchema(Schema):
    """Schema untuk PATCH course — semua field opsional."""
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    price: Optional[float] = None
    is_published: Optional[bool] = None


# ═══════════════════════════════════════════════════════════════
# ENROLLMENT SCHEMAS
# ═══════════════════════════════════════════════════════════════

class EnrollSchema(Schema):
    course_id: int


class EnrollmentOut(Schema):
    id: int
    course: CourseOut
    status: str
    enrolled_at: datetime

    class Config:
        from_attributes = True


class ProgressUpdateSchema(Schema):
    """Schema untuk update progress lesson."""
    lesson_id: int
    is_completed: bool = True
    last_position_seconds: int = 0


class ProgressOut(Schema):
    lesson_id: int
    lesson_title: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    last_position_seconds: int

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# GENERIC RESPONSE
# ═══════════════════════════════════════════════════════════════

class MessageOut(Schema):
    message: str
    success: bool = True