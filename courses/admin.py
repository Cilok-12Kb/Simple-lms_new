"""
courses/admin.py
Konfigurasi Django Admin untuk Simple LMS
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Category, Course, Lesson, Enrollment, Progress


# ─────────────────────────────────────────────────────────────
# USER ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin untuk custom User model.
    Extends BaseUserAdmin agar form login/password tetap berfungsi.
    """
    list_display = ('username', 'email', 'get_full_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    list_per_page = 25

    # Tambahkan field 'role' dan 'bio' ke form edit user
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Info LMS', {
            'fields': ('role', 'bio', 'avatar'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Info LMS', {
            'fields': ('role',),
        }),
    )


# ─────────────────────────────────────────────────────────────
# CATEGORY ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'course_count', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}   # Slug otomatis dari name
    ordering = ('parent', 'name')

    def course_count(self, obj):
        """Tampilkan jumlah course di kategori ini."""
        count = obj.courses.count()
        return format_html('<b>{}</b>', count)
    course_count.short_description = 'Jumlah Course'


# ─────────────────────────────────────────────────────────────
# LESSON INLINE (untuk ditampilkan di dalam Course admin)
# ─────────────────────────────────────────────────────────────

class LessonInline(admin.TabularInline):
    """
    Inline model: Lesson ditampilkan langsung di halaman edit Course.
    Sehingga kita bisa tambah/edit lesson tanpa pindah halaman.
    """
    model = Lesson
    extra = 1                  # Tampilkan 1 form kosong untuk tambah lesson baru
    fields = ('order', 'title', 'content_type', 'duration_minutes', 'is_free_preview')
    ordering = ('order',)


# ─────────────────────────────────────────────────────────────
# COURSE ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'instructor', 'category', 'level',
        'price', 'is_published', 'enrollment_count', 'lesson_count', 'created_at'
    )
    list_filter = ('is_published', 'level', 'category', 'instructor')
    search_fields = ('title', 'description', 'instructor__username')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)
    list_per_page = 20
    list_editable = ('is_published', 'price')   # Bisa edit langsung dari list view
    date_hierarchy = 'created_at'

    # Tampilkan LessonInline di halaman edit Course
    inlines = [LessonInline]

    # Grouping field di halaman edit
    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('title', 'slug', 'description', 'thumbnail'),
        }),
        ('Pengajar & Kategori', {
            'fields': ('instructor', 'category', 'level'),
        }),
        ('Harga & Status', {
            'fields': ('price', 'is_published'),
        }),
    )

    def enrollment_count(self, obj):
        count = obj.enrollments.count()
        return format_html('<span style="color: #1a7fd4;">{} siswa</span>', count)
    enrollment_count.short_description = 'Enrollment'

    def lesson_count(self, obj):
        count = obj.lessons.count()
        return count
    lesson_count.short_description = 'Lessons'

    def get_queryset(self, request):
        """Override queryset untuk optimasi — hindari N+1 di list view."""
        return super().get_queryset(request).select_related(
            'instructor', 'category'
        ).annotate(
            _enrollment_count=__import__(
                'django.db.models', fromlist=['Count']
            ).Count('enrollments', distinct=True),
        )


# ─────────────────────────────────────────────────────────────
# LESSON ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'content_type', 'order', 'duration_minutes', 'is_free_preview')
    list_filter = ('content_type', 'is_free_preview', 'course')
    search_fields = ('title', 'content', 'course__title')
    ordering = ('course', 'order')
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('course')


# ─────────────────────────────────────────────────────────────
# PROGRESS INLINE (untuk ditampilkan di dalam Enrollment admin)
# ─────────────────────────────────────────────────────────────

class ProgressInline(admin.TabularInline):
    model = Progress
    extra = 0
    fields = ('lesson', 'is_completed', 'completed_at', 'last_position_seconds')
    readonly_fields = ('completed_at',)
    ordering = ('lesson__order',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('lesson')


# ─────────────────────────────────────────────────────────────
# ENROLLMENT ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'student', 'course', 'status', 'progress_percentage',
        'enrolled_at', 'completed_at'
    )
    list_filter = ('status', 'enrolled_at', 'course')
    search_fields = ('student__username', 'course__title')
    ordering = ('-enrolled_at',)
    readonly_fields = ('enrolled_at', 'completed_at')
    list_per_page = 25

    inlines = [ProgressInline]

    def progress_percentage(self, obj):
        """Hitung dan tampilkan persentase progress."""
        total = obj.course.lessons.count()
        if total == 0:
            return '–'
        completed = obj.progress_records.filter(is_completed=True).count()
        pct = int((completed / total) * 100)
        color = '#27ae60' if pct == 100 else '#e67e22' if pct > 0 else '#e74c3c'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, f'{pct}%'
        )
    progress_percentage.short_description = 'Progress'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student', 'course'
        ).prefetch_related('progress_records')


# ─────────────────────────────────────────────────────────────
# PROGRESS ADMIN
# ─────────────────────────────────────────────────────────────

@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed',)
    search_fields = ('enrollment__student__username', 'lesson__title')
    readonly_fields = ('completed_at',)
    ordering = ('-completed_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'enrollment__student', 'lesson'
        )