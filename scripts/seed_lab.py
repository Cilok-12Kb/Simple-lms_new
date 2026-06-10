"""
scripts/seed_lab.py
Seed data khusus untuk Lab Praktikum 5.
Membuat data dalam jumlah besar agar N+1 problem terlihat jelas di Silk.
"""
import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Category, Course, Lesson, Enrollment
from django.db.models import Count

User = get_user_model()


def run():
    print("=" * 55)
    print("🌱 SEED DATA LAB 5 — Skala Besar")
    print("=" * 55)

    # ── 1. Pastikan ada instructor ──────────────────────────
    print("\n👤 Memastikan instructors tersedia...")
    instructors = []
    for i in range(1, 6):  # 5 instructors
        user, created = User.objects.get_or_create(
            username=f'lab_instructor_{i:02d}',
            defaults={
                'first_name': f'Dosen',
                'last_name': f'{i:02d}',
                'email': f'dosen{i}@lab.com',
                'role': 'instructor',
                'is_active': True,
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        instructors.append(user)
    print(f"   ✅ {len(instructors)} instructors siap.")

    # ── 2. Pastikan ada students ────────────────────────────
    print("\n👤 Memastikan students tersedia...")
    students = []
    for i in range(1, 21):  # 20 students
        user, created = User.objects.get_or_create(
            username=f'lab_student_{i:02d}',
            defaults={
                'first_name': f'Siswa',
                'last_name': f'{i:02d}',
                'email': f'siswa{i}@lab.com',
                'role': 'student',
                'is_active': True,
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        students.append(user)
    print(f"   ✅ {len(students)} students siap.")

    # ── 3. Pastikan ada category ────────────────────────────
    category, _ = Category.objects.get_or_create(
        slug='lab-category',
        defaults={'name': 'Lab Category', 'description': 'Untuk keperluan lab'}
    )

    # ── 4. Buat 100+ courses dengan bulk_create ─────────────
    print("\n📚 Membuat courses (target: 100+)...")
    existing_count = Course.objects.count()
    if existing_count >= 100:
        print(f"   [SKIP] Sudah ada {existing_count} courses.")
    else:
        needed = 100 - existing_count
        import random
        levels = ['beginner', 'intermediate', 'advanced']
        courses_to_create = []
        for i in range(existing_count + 1, existing_count + needed + 1):
            courses_to_create.append(Course(
                title=f'Course Lab {i:03d} — {random.choice(["Django", "Python", "Docker", "DRF", "SQL"])}',
                slug=f'course-lab-{i:03d}',
                description=f'Deskripsi course lab nomor {i}. Konten pembelajaran backend development.',
                instructor=random.choice(instructors),
                category=category,
                level=random.choice(levels),
                price=random.choice([50000, 100000, 150000, 200000, 250000]),
                is_published=True,
            ))
        Course.objects.bulk_create(courses_to_create, ignore_conflicts=True)
        print(f"   ✅ {len(courses_to_create)} courses dibuat. Total: {Course.objects.count()}")

    # ── 5. Buat lessons untuk setiap course ─────────────────
    print("\n📝 Membuat lessons untuk courses yang belum punya...")
    courses_without_lessons = Course.objects.annotate(
        lesson_count=Count('lessons')
    ).filter(lesson_count=0)[:30]  # Batas 30 agar tidak terlalu lama

    lessons_to_create = []
    content_types = ['video', 'text', 'quiz']
    import random
    for course in courses_without_lessons:
        for order in range(random.randint(3, 7)):
            lessons_to_create.append(Lesson(
                course=course,
                title=f'Pelajaran {order + 1} — {course.title[:30]}',
                content_type=random.choice(content_types),
                duration_minutes=random.randint(10, 45),
                order=order,
                is_free_preview=(order == 0),
            ))

    if lessons_to_create:
        Lesson.objects.bulk_create(lessons_to_create)
        print(f"   ✅ {len(lessons_to_create)} lessons dibuat.")

    # ── 6. Buat enrollments ──────────────────────────────────
    print("\n🎓 Membuat enrollments...")
    all_courses = list(Course.objects.filter(is_published=True)[:50])
    enroll_to_create = []
    existing_pairs = set(
        Enrollment.objects.values_list('student_id', 'course_id')
    )
    for student in students:
        selected = random.sample(all_courses, min(5, len(all_courses)))
        for course in selected:
            if (student.id, course.id) not in existing_pairs:
                existing_pairs.add((student.id, course.id))
                enroll_to_create.append(Enrollment(
                    student=student,
                    course=course,
                    status='active',
                ))

    if enroll_to_create:
        Enrollment.objects.bulk_create(enroll_to_create, ignore_conflicts=True)
        print(f"   ✅ {len(enroll_to_create)} enrollments dibuat.")

    # ── Ringkasan ───────────────────────────────────────────
    print("\n" + "=" * 55)
    print("✅ SELESAI! Ringkasan data:")
    print(f"   Instructors : {User.objects.filter(role='instructor').count()}")
    print(f"   Students    : {User.objects.filter(role='student').count()}")
    print(f"   Courses     : {Course.objects.count()}")
    print(f"   Lessons     : {Lesson.objects.count()}")
    print(f"   Enrollments : {Enrollment.objects.count()}")
    print("=" * 55)


if __name__ == '__main__':
    run()