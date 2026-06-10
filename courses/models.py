"""
courses/models.py
Models untuk Simple LMS — Pemrograman Sisi Server
Universitas Dian Nuswantoro
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .managers import CourseManager, EnrollmentManager

# ═══════════════════════════════════════════════════════════════
# 1. CUSTOM USER MODEL
# Extends AbstractUser agar bisa tambah field 'role'
# ═══════════════════════════════════════════════════════════════

class User(AbstractUser):
    """
    Custom User model dengan tambahan field 'role'.
    Menggunakan AbstractUser agar semua fitur bawaan Django
    (login, password, permissions) tetap berfungsi.
    """
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    role = models.CharField(
        'Peran',
        max_length=20,
        choices=ROLE_CHOICES,
        default='student',
    )
    bio = models.TextField('Bio', blank=True, default='')
    avatar = models.ImageField(
        'Avatar',
        upload_to='avatars/',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Pengguna'
        verbose_name_plural = 'Pengguna'
        db_table = 'lms_user'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_instructor(self):
        return self.role == 'instructor'

    @property
    def is_student(self):
        return self.role == 'student'


# ═══════════════════════════════════════════════════════════════
# 2. CATEGORY MODEL
# Self-referencing (hierarki): Category bisa punya parent Category
# Contoh: "Programming" → "Web Development" → "Django"
# ═══════════════════════════════════════════════════════════════

class Category(models.Model):
    """
    Kategori course dengan self-referencing untuk hierarki.
    Contoh hierarki:
        Programming (parent=None)
        ├── Web Development (parent=Programming)
        │   ├── Django (parent=Web Development)
        │   └── React (parent=Web Development)
        └── Data Science (parent=Programming)
    """
    name = models.CharField('Nama Kategori', max_length=100)
    slug = models.SlugField('Slug', max_length=100, unique=True)
    description = models.TextField('Deskripsi', blank=True, default='')
    parent = models.ForeignKey(
        'self',                       # ← self-referencing FK
        verbose_name='Kategori Induk',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',      # akses: category.children.all()
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategori'
        db_table = 'lms_category'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug'], name='idx_category_slug'),
            models.Index(fields=['parent'], name='idx_category_parent'),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} › {self.name}"
        return self.name

    @property
    def is_root(self):
        """True jika kategori ini tidak punya parent (kategori tingkat atas)."""
        return self.parent is None


# ═══════════════════════════════════════════════════════════════
# 3. COURSE MODEL
# ═══════════════════════════════════════════════════════════════

class Course(models.Model):
    """
    Model utama course/mata kuliah.
    Relasi:
    - instructor (FK ke User, instructor yang buat course)
    - category (FK ke Category)
    """
    LEVEL_CHOICES = [
        ('beginner', 'Pemula'),
        ('intermediate', 'Menengah'),
        ('advanced', 'Lanjutan'),
    ]

    title = models.CharField('Judul', max_length=200)
    slug = models.SlugField('Slug', max_length=200, unique=True)
    description = models.TextField('Deskripsi', blank=True, default='')
    thumbnail = models.ImageField(
        'Thumbnail',
        upload_to='course_thumbnails/',
        null=True,
        blank=True,
    )
    instructor = models.ForeignKey(
        User,
        verbose_name='Instruktur',
        on_delete=models.RESTRICT,      # Tidak bisa hapus user jika masih punya course
        related_name='courses_taught',  # akses: user.courses_taught.all()
        limit_choices_to={'role': 'instructor'},
    )
    category = models.ForeignKey(
        Category,
        verbose_name='Kategori',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
    )
    level = models.CharField(
        'Level',
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner',
    )
    price = models.DecimalField(
        'Harga',
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    is_published = models.BooleanField('Dipublikasikan', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = CourseManager()

    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        db_table = 'lms_course'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug'], name='idx_course_slug'),
            models.Index(fields=['instructor'], name='idx_course_instructor'),
            models.Index(fields=['category'], name='idx_course_category'),
            models.Index(fields=['is_published', '-created_at'],
                         name='idx_course_published_date'),
            # ← TAMBAHKAN INDEX BARU INI untuk Lab 5:
            # Index untuk filter berdasarkan harga (sering dipakai di dashboard)
            models.Index(fields=['price'], name='idx_course_price'),

            # Composite index: instructor + is_published
            # Untuk query: "tampilkan course published milik instructor X"
            models.Index(fields=['instructor', 'is_published'],
                         name='idx_course_inst_pub'),

            # Index untuk level (sering difilter di listing)
            models.Index(fields=['level'], name='idx_course_level'),
        ]

    def __str__(self):
        return self.title

    @property
    def total_lessons(self):
        return self.lessons.count()

    @property
    def total_enrollments(self):
        return self.enrollments.count()


# ═══════════════════════════════════════════════════════════════
# 4. LESSON MODEL
# Dengan ordering field untuk urutan tampil
# ═══════════════════════════════════════════════════════════════

class Lesson(models.Model):
    """
    Pelajaran/konten di dalam course.
    Punya field 'order' untuk menentukan urutan tampil.
    """
    CONTENT_TYPE_CHOICES = [
        ('video', 'Video'),
        ('text', 'Teks/Artikel'),
        ('quiz', 'Kuis'),
        ('assignment', 'Tugas'),
    ]

    course = models.ForeignKey(
        Course,
        verbose_name='Course',
        on_delete=models.CASCADE,        # Hapus course → lesson ikut terhapus
        related_name='lessons',          # akses: course.lessons.all()
    )
    title = models.CharField('Judul Pelajaran', max_length=200)
    content_type = models.CharField(
        'Tipe Konten',
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='video',
    )
    content = models.TextField('Konten/Deskripsi', blank=True, default='')
    video_url = models.URLField('URL Video', blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(
        'Durasi (menit)',
        default=0,
    )
    order = models.PositiveIntegerField(
        'Urutan',
        default=0,
        help_text='Urutan tampil lesson dalam course (0 = pertama)',
    )
    is_free_preview = models.BooleanField(
        'Bisa Diakses Gratis',
        default=False,
        help_text='Jika True, lesson bisa diakses tanpa enrollment',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pelajaran'
        verbose_name_plural = 'Pelajaran'
        db_table = 'lms_lesson'
        ordering = ['course', 'order']   # Default urut berdasarkan course, lalu order
        indexes = [
            models.Index(fields=['course', 'order'], name='idx_lesson_course_order'),
        ]

    def __str__(self):
        return f"[{self.order}] {self.title} ({self.course.title})"


# ═══════════════════════════════════════════════════════════════
# 5. ENROLLMENT MODEL
# Many-to-many antara User dan Course, dengan unique constraint
# ═══════════════════════════════════════════════════════════════

class Enrollment(models.Model):
    """
    Pendaftaran siswa ke course.
    Unique constraint: satu user hanya bisa enrollment 1x per course.
    """
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('completed', 'Selesai'),
        ('dropped', 'Berhenti'),
    ]

    student = models.ForeignKey(
        User,
        verbose_name='Siswa',
        on_delete=models.CASCADE,
        related_name='enrollments',      # akses: user.enrollments.all()
        limit_choices_to={'role': 'student'},
    )
    course = models.ForeignKey(
        Course,
        verbose_name='Course',
        on_delete=models.CASCADE,
        related_name='enrollments',      # akses: course.enrollments.all()
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
    )
    enrolled_at = models.DateTimeField(
        'Tanggal Daftar',
        auto_now_add=True,
    )
    completed_at = models.DateTimeField(
        'Tanggal Selesai',
        null=True,
        blank=True,
    )
    objects = EnrollmentManager()

    class Meta:
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        db_table = 'lms_enrollment'
        # UNIQUE CONSTRAINT: satu user tidak bisa daftar course yang sama dua kali
        unique_together = [['student', 'course']]
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['student', 'status'], name='idx_enrollment_student_status'),
            models.Index(fields=['course', 'status'], name='idx_enrollment_course_status'),
            # ← TAMBAHKAN:
            # Index untuk filter enrollment by course + status
            # Dipakai di dashboard_optimized untuk COUNT active enrollments
            models.Index(fields=['course', 'status', 'enrolled_at'],
                         name='idx_enroll_course_stat_date'),
        ]

    def __str__(self):
        return f"{self.student.username} → {self.course.title} ({self.status})"

    def mark_completed(self):
        """Tandai enrollment sebagai selesai."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


# ═══════════════════════════════════════════════════════════════
# 6. PROGRESS MODEL
# Tracking penyelesaian lesson per enrollment
# ═══════════════════════════════════════════════════════════════

class Progress(models.Model):
    """
    Tracking progress belajar siswa per lesson.
    Setiap kali siswa menyelesaikan lesson, dibuat satu record Progress.
    """
    enrollment = models.ForeignKey(
        Enrollment,
        verbose_name='Enrollment',
        on_delete=models.CASCADE,
        related_name='progress_records',
    )
    lesson = models.ForeignKey(
        Lesson,
        verbose_name='Pelajaran',
        on_delete=models.CASCADE,
        related_name='progress_records',
    )
    is_completed = models.BooleanField('Selesai', default=False)
    completed_at = models.DateTimeField(
        'Waktu Selesai',
        null=True,
        blank=True,
    )
    # Menyimpan posisi terakhir video (dalam detik) untuk resume
    last_position_seconds = models.PositiveIntegerField(
        'Posisi Terakhir (detik)',
        default=0,
    )

    class Meta:
        verbose_name = 'Progress'
        verbose_name_plural = 'Progress'
        db_table = 'lms_progress'
        # Unique: satu enrollment hanya punya satu progress per lesson
        unique_together = [['enrollment', 'lesson']]
        indexes = [
            models.Index(fields=['enrollment', 'is_completed'],
                         name='idx_progress_enroll_done'),
        ]

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.enrollment.student.username} — {self.lesson.title}"

    def mark_complete(self):
        """Tandai lesson ini sebagai selesai."""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=['is_completed', 'completed_at'])