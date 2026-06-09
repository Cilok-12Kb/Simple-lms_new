"""
scripts/seed_data.py
Script untuk mengisi database dengan data awal (seed data).
Jalankan dengan: docker compose exec web python scripts/seed_data.py
"""
import os
import sys
import django

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

# Setup Django environment agar script bisa dijalankan standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import User, Category, Course, Lesson, Enrollment, Progress
from django.utils.text import slugify


def clear_data():
    """Hapus semua data lama (hati-hati di production!)."""
    print("🗑️  Menghapus data lama...")
    Progress.objects.all().delete()
    Enrollment.objects.all().delete()
    Lesson.objects.all().delete()
    Course.objects.all().delete()
    Category.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    print("✅ Data lama berhasil dihapus.\n")


def seed_users():
    """Buat users dengan berbagai role."""
    print("👤 Membuat users...")

    # Instructors
    instructors_data = [
        {'username': 'budi_instructor', 'first_name': 'Budi', 'last_name': 'Santoso',
         'email': 'budi@lms.com', 'role': 'instructor'},
        {'username': 'sari_instructor', 'first_name': 'Sari', 'last_name': 'Dewi',
         'email': 'sari@lms.com', 'role': 'instructor'},
        {'username': 'andi_instructor', 'first_name': 'Andi', 'last_name': 'Wijaya',
         'email': 'andi@lms.com', 'role': 'instructor'},
    ]

    instructors = []
    for data in instructors_data:
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={**data, 'is_active': True}
        )
        if created:
            user.set_password('password123')
            user.save()
        instructors.append(user)
        print(f"   {'[BARU]' if created else '[ADA] '} Instructor: {user.get_full_name()}")

    # Students
    students_data = [
        {'username': f'student_{i:02d}', 'first_name': f'Siswa', 'last_name': f'{i:02d}',
         'email': f'student{i}@lms.com', 'role': 'student'}
        for i in range(1, 11)  # 10 students
    ]

    students = []
    for data in students_data:
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={**data, 'is_active': True}
        )
        if created:
            user.set_password('password123')
            user.save()
        students.append(user)

    print(f"   ✅ {len(students)} students dibuat.\n")
    return instructors, students


def seed_categories():
    """Buat kategori dengan hierarki."""
    print("📁 Membuat kategori...")

    # Root categories
    programming, _ = Category.objects.get_or_create(
        slug='programming',
        defaults={'name': 'Pemrograman', 'description': 'Semua tentang coding'}
    )
    design, _ = Category.objects.get_or_create(
        slug='design',
        defaults={'name': 'Desain', 'description': 'UI/UX dan desain grafis'}
    )

    # Sub categories
    web_dev, _ = Category.objects.get_or_create(
        slug='web-development',
        defaults={'name': 'Web Development', 'parent': programming,
                  'description': 'Pengembangan web frontend dan backend'}
    )
    backend, _ = Category.objects.get_or_create(
        slug='backend-development',
        defaults={'name': 'Backend Development', 'parent': web_dev,
                  'description': 'Server-side development'}
    )
    data_science, _ = Category.objects.get_or_create(
        slug='data-science',
        defaults={'name': 'Data Science', 'parent': programming,
                  'description': 'Analisis data dan machine learning'}
    )

    print(f"   ✅ Kategori dibuat: {programming}, {web_dev}, {backend}, {design}, {data_science}\n")
    return backend, web_dev, data_science


def seed_courses(instructors, categories):
    """Buat courses."""
    print("📚 Membuat courses...")

    backend_cat, web_cat, ds_cat = categories

    courses_data = [
        {
            'title': 'Python untuk Pemula',
            'slug': 'python-pemula',
            'description': 'Belajar Python dari nol sampai bisa membuat program sederhana.',
            'instructor': instructors[0],
            'category': web_cat,
            'level': 'beginner',
            'price': 150000,
            'is_published': True,
        },
        {
            'title': 'Django Web Framework',
            'slug': 'django-web-framework',
            'description': 'Membangun aplikasi web dengan Django, ORM, dan REST API.',
            'instructor': instructors[0],
            'category': backend_cat,
            'level': 'intermediate',
            'price': 250000,
            'is_published': True,
        },
        {
            'title': 'Docker & DevOps Dasar',
            'slug': 'docker-devops-dasar',
            'description': 'Containerization dengan Docker dan Docker Compose.',
            'instructor': instructors[1],
            'category': backend_cat,
            'level': 'intermediate',
            'price': 200000,
            'is_published': True,
        },
        {
            'title': 'Data Analysis dengan Pandas',
            'slug': 'data-analysis-pandas',
            'description': 'Analisis data menggunakan Python Pandas dan Matplotlib.',
            'instructor': instructors[2],
            'category': ds_cat,
            'level': 'beginner',
            'price': 175000,
            'is_published': True,
        },
        {
            'title': 'React.js Modern',
            'slug': 'reactjs-modern',
            'description': 'Frontend development dengan React Hooks dan modern tooling.',
            'instructor': instructors[1],
            'category': web_cat,
            'level': 'intermediate',
            'price': 220000,
            'is_published': False,   # Draft
        },
    ]

    courses = []
    for data in courses_data:
        course, created = Course.objects.get_or_create(
            slug=data['slug'],
            defaults=data
        )
        courses.append(course)
        print(f"   {'[BARU]' if created else '[ADA] '} Course: {course.title}")

    print()
    return courses


def seed_lessons(courses):
    """Buat lessons untuk setiap course menggunakan bulk_create."""
    print("📝 Membuat lessons (bulk_create)...")

    all_lessons = []
    lesson_templates = {
        0: [  # Python untuk Pemula
            ('Pengenalan Python', 'video', 15),
            ('Instalasi & Setup Environment', 'video', 20),
            ('Variabel dan Tipe Data', 'text', 10),
            ('Kondisi dan Perulangan', 'video', 25),
            ('Fungsi dan Module', 'video', 30),
            ('OOP Dasar', 'video', 35),
            ('File I/O', 'text', 15),
            ('Project Akhir', 'assignment', 60),
        ],
        1: [  # Django Web Framework
            ('Pengenalan Django', 'video', 20),
            ('Setup Project Django', 'video', 25),
            ('Models dan ORM', 'video', 40),
            ('Views dan URL Routing', 'video', 35),
            ('Templates', 'video', 30),
            ('Forms dan Validasi', 'video', 40),
            ('Authentication', 'video', 35),
            ('REST API dengan DRF', 'video', 50),
        ],
        2: [  # Docker & DevOps
            ('Pengenalan Container', 'video', 15),
            ('Instalasi Docker', 'video', 20),
            ('Docker Images dan Containers', 'video', 30),
            ('Dockerfile', 'text', 25),
            ('Docker Compose', 'video', 40),
            ('Networking di Docker', 'video', 35),
            ('Volumes dan Persistence', 'video', 30),
            ('Deploy ke Production', 'assignment', 60),
        ],
    }

    for idx, course in enumerate(courses[:3]):  # Buat lesson untuk 3 course pertama
        # Cek apakah sudah ada lessons
        if course.lessons.exists():
            print(f"   [SKIP] Lessons untuk '{course.title}' sudah ada.")
            continue

        templates = lesson_templates.get(idx, [])
        for order, (title, content_type, duration) in enumerate(templates):
            all_lessons.append(
                Lesson(
                    course=course,
                    title=title,
                    content_type=content_type,
                    duration_minutes=duration,
                    order=order,
                    is_free_preview=(order == 0),  # Lesson pertama gratis
                    content=f'Konten pelajaran: {title}',
                )
            )

    if all_lessons:
        # bulk_create: semua lesson dibuat dalam 1 query SQL!
        Lesson.objects.bulk_create(all_lessons)
        print(f"   ✅ {len(all_lessons)} lessons dibuat dengan bulk_create.\n")
    else:
        print("   [SKIP] Semua lessons sudah ada.\n")


def seed_enrollments(students, courses):
    """Buat enrollments dan progress."""
    print("🎓 Membuat enrollments...")

    published_courses = [c for c in courses if c.is_published]
    enrollments_to_create = []
    enrollment_pairs = set()

    for student in students:
        # Setiap student mendaftar ke 2-3 course acak
        import random
        num_courses = random.randint(2, min(3, len(published_courses)))
        selected = random.sample(published_courses, num_courses)

        for course in selected:
            pair = (student.id, course.id)
            if pair not in enrollment_pairs:
                enrollment_pairs.add(pair)
                enrollments_to_create.append(
                    Enrollment(
                        student=student,
                        course=course,
                        status='active',
                    )
                )

    # bulk_create untuk enrollments
    created = Enrollment.objects.bulk_create(
        enrollments_to_create,
        ignore_conflicts=True  # Skip jika sudah ada (unique_together)
    )
    print(f"   ✅ {len(created)} enrollments dibuat.\n")

    # Buat beberapa progress records
    print("📊 Membuat progress records...")
    all_enrollments = Enrollment.objects.select_related('course').prefetch_related(
        'course__lessons'
    )[:20]  # Ambil 20 enrollment pertama

    progress_to_create = []
    for enrollment in all_enrollments:
        lessons = list(enrollment.course.lessons.all())
        if not lessons:
            continue

        import random
        num_completed = random.randint(0, len(lessons))
        completed_lessons = random.sample(lessons, num_completed)

        for lesson in lessons:
            is_completed = lesson in completed_lessons
            progress_to_create.append(
                Progress(
                    enrollment=enrollment,
                    lesson=lesson,
                    is_completed=is_completed,
                    last_position_seconds=random.randint(0, lesson.duration_minutes * 60),
                )
            )

    if progress_to_create:
        Progress.objects.bulk_create(progress_to_create, ignore_conflicts=True)
        print(f"   ✅ {len(progress_to_create)} progress records dibuat.\n")


def run():
    """Jalankan semua seed functions."""
    print("=" * 60)
    print("🌱 SEED DATA — Simple LMS")
    print("=" * 60)
    print()

    # Uncomment baris di bawah jika ingin mulai dari data bersih:
    # clear_data()

    instructors, students = seed_users()
    categories = seed_categories()
    courses = seed_courses(instructors, categories)
    seed_lessons(courses)
    seed_enrollments(students, courses)

    print("=" * 60)
    print("✅ SELESAI! Data berhasil di-seed.")
    print("=" * 60)
    print()
    print("Ringkasan:")
    print(f"  Users (instructor) : {User.objects.filter(role='instructor').count()}")
    print(f"  Users (student)    : {User.objects.filter(role='student').count()}")
    print(f"  Categories         : {Category.objects.count()}")
    print(f"  Courses            : {Course.objects.count()}")
    print(f"  Lessons            : {Lesson.objects.count()}")
    print(f"  Enrollments        : {Enrollment.objects.count()}")
    print(f"  Progress records   : {Progress.objects.count()}")


if __name__ == '__main__':
    run()