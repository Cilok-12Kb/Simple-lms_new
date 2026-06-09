"""
scripts/query_demo.py
Demo N+1 Problem dan Query Optimization pada Simple LMS.
Jalankan dengan: docker compose exec web python scripts/query_demo.py
"""
import os
import sys
import time
import django

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from django.db.models import Count, Avg, Q
from courses.models import Course, Enrollment, Lesson, Progress

# Aktifkan logging query Django
settings.DEBUG = True


# ─────────────────────────────────────────────────────────────
# UTILITY: Fungsi untuk benchmark
# ─────────────────────────────────────────────────────────────

def benchmark(label, func, show_queries=False):
    """Jalankan func dan tampilkan jumlah query + waktu."""
    reset_queries()
    start = time.perf_counter()

    result = func()

    elapsed_ms = (time.perf_counter() - start) * 1000
    query_count = len(connection.queries)

    print(f"\n{'─'*55}")
    print(f"  📌 {label}")
    print(f"  ⚡ Jumlah Query : {query_count}")
    print(f"  ⏱️  Waktu        : {elapsed_ms:.2f}ms")

    if show_queries and connection.queries:
        print(f"\n  Query yang dijalankan:")
        for i, q in enumerate(connection.queries, 1):
            sql_preview = q['sql'][:100] + ('...' if len(q['sql']) > 100 else '')
            print(f"    [{i}] ({q['time']}s) {sql_preview}")

    print(f"{'─'*55}")
    return result, query_count, elapsed_ms


def separator(title):
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print(f"{'═'*55}")


# ─────────────────────────────────────────────────────────────
# DEMO 1: N+1 Problem — Daftar Course + Nama Instructor
# ─────────────────────────────────────────────────────────────

separator("DEMO 1: Course List + Instructor Name")

def demo1_bad():
    """❌ N+1 Problem: setiap akses course.instructor.username = query baru."""
    courses = Course.objects.all()
    result = []
    for course in courses:
        result.append({
            'title': course.title,
            'instructor': course.instructor.username,  # ← N+1 di sini!
        })
    return result

def demo1_good():
    """✅ Optimasi dengan select_related (JOIN): 1 query untuk semua."""
    courses = Course.objects.select_related('instructor').all()
    result = []
    for course in courses:
        result.append({
            'title': course.title,
            'instructor': course.instructor.username,  # Tidak ada query baru!
        })
    return result

_, q_bad, t_bad = benchmark("❌ TANPA OPTIMASI (N+1 Problem)", demo1_bad)
_, q_good, t_good = benchmark("✅ DENGAN select_related", demo1_good)

print(f"\n  📊 Perbandingan Demo 1:")
print(f"     Query : {q_bad} → {q_good} (hemat {q_bad - q_good} queries)")
if t_bad > 0:
    pct = ((t_bad - t_good) / t_bad) * 100
    print(f"     Waktu : {t_bad:.2f}ms → {t_good:.2f}ms (improvement: {pct:.0f}%)")


# ─────────────────────────────────────────────────────────────
# DEMO 2: N+1 Problem — Course + Jumlah Enrollment
# ─────────────────────────────────────────────────────────────

separator("DEMO 2: Course List + Enrollment Count")

def demo2_bad():
    """❌ N+1: menghitung enrollment per course dengan query terpisah."""
    courses = Course.objects.all()
    result = []
    for course in courses:
        count = Enrollment.objects.filter(course=course).count()  # ← N+1!
        result.append({'title': course.title, 'enrollments': count})
    return result

def demo2_good():
    """✅ Optimasi dengan annotate: hitung di database, 1 query."""
    courses = Course.objects.annotate(
        enrollment_count=Count('enrollments', distinct=True)
    )
    result = []
    for course in courses:
        result.append({'title': course.title, 'enrollments': course.enrollment_count})
    return result

_, q_bad, t_bad = benchmark("❌ TANPA OPTIMASI (Count dalam loop)", demo2_bad)
_, q_good, t_good = benchmark("✅ DENGAN annotate(Count)", demo2_good)

print(f"\n  📊 Perbandingan Demo 2:")
print(f"     Query : {q_bad} → {q_good} (hemat {q_bad - q_good} queries)")


# ─────────────────────────────────────────────────────────────
# DEMO 3: Multi-level N+1 — Course + Lessons + Instructor
# ─────────────────────────────────────────────────────────────

separator("DEMO 3: Course + Lessons + Instructor (multi-level)")

def demo3_bad():
    """❌ N+1 berlapis: akses relasi di beberapa level."""
    courses = Course.objects.all()
    result = []
    for course in courses:
        lessons = Lesson.objects.filter(course=course)  # ← N+1 level 1
        lesson_list = [l.title for l in lessons]
        result.append({
            'title': course.title,
            'instructor': course.instructor.get_full_name(),  # ← N+1 level 2
            'lessons': lesson_list,
        })
    return result

def demo3_good():
    """✅ Kombinasi select_related + prefetch_related."""
    courses = Course.objects.select_related(
        'instructor'         # ForeignKey → JOIN
    ).prefetch_related(
        'lessons'            # Reverse FK → separate optimized query
    )
    result = []
    for course in courses:
        result.append({
            'title': course.title,
            'instructor': course.instructor.get_full_name(),  # Sudah di-JOIN
            'lessons': [l.title for l in course.lessons.all()],  # Dari prefetch
        })
    return result

_, q_bad, t_bad = benchmark("❌ TANPA OPTIMASI (multi-level N+1)", demo3_bad)
_, q_good, t_good = benchmark("✅ DENGAN select_related + prefetch_related", demo3_good)

print(f"\n  📊 Perbandingan Demo 3:")
print(f"     Query : {q_bad} → {q_good} (hemat {q_bad - q_good} queries)")


# ─────────────────────────────────────────────────────────────
# DEMO 4: Custom Manager — for_listing() dan for_student_dashboard()
# ─────────────────────────────────────────────────────────────

separator("DEMO 4: Custom Manager — Course.objects.for_listing()")

def demo4_manager():
    """✅ Menggunakan custom manager yang sudah dioptimasi."""
    courses = Course.objects.for_listing()
    result = []
    for course in courses:
        result.append({
            'title': course.title,
            'instructor': course.instructor.username,
            'enrollments': course.enrollment_count,
            'lessons': course.lesson_count,
        })
    return result

_, q, t = benchmark("✅ Course.objects.for_listing()", demo4_manager, show_queries=True)


# ─────────────────────────────────────────────────────────────
# DEMO 5: Aggregate — Statistik keseluruhan
# ─────────────────────────────────────────────────────────────

separator("DEMO 5: Aggregate — Statistik LMS")

def demo5_bad():
    """❌ Banyak query terpisah untuk statistik."""
    from django.db.models import Max, Min, Avg
    total_courses = Course.objects.count()
    total_lessons = Lesson.objects.count()
    total_enrollments = Enrollment.objects.count()
    avg_price = Course.objects.aggregate(avg=Avg('price'))['avg']
    max_price = Course.objects.aggregate(max=Max('price'))['max']
    return {
        'courses': total_courses, 'lessons': total_lessons,
        'enrollments': total_enrollments, 'avg_price': avg_price,
    }

def demo5_good():
    """✅ Satu aggregate query untuk semua statistik."""
    from django.db.models import Max, Min, Avg
    stats = Course.objects.aggregate(
        total_courses=Count('id'),
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price'),
    )
    total_lessons = Lesson.objects.count()       # Berbeda model, query terpisah OK
    total_enrollments = Enrollment.objects.count()
    return {**stats, 'total_lessons': total_lessons, 'total_enrollments': total_enrollments}

_, q_bad, t_bad = benchmark("❌ TANPA OPTIMASI (5 query terpisah)", demo5_bad)
_, q_good, t_good = benchmark("✅ DENGAN aggregate() gabungan", demo5_good)

print(f"\n  📊 Perbandingan Demo 5:")
print(f"     Query : {q_bad} → {q_good} (hemat {q_bad - q_good} queries)")


# ─────────────────────────────────────────────────────────────
# RINGKASAN AKHIR
# ─────────────────────────────────────────────────────────────

separator("RINGKASAN HASIL OPTIMASI")
print("""
  Teknik yang didemonstrasikan:
  
  1. select_related   → Untuk ForeignKey (JOIN ke 1 tabel)
                        Contoh: course.instructor
  
  2. prefetch_related → Untuk Reverse FK / ManyToMany
                        Contoh: course.lessons.all()
  
  3. annotate(Count)  → Hitung relasi di database, bukan Python
                        Menggantikan loop + count() terpisah
  
  4. aggregate()      → Statistik keseluruhan dalam 1 query
                        Max, Min, Avg, Count sekaligus
  
  5. Custom Manager   → Encapsulate query yang sering dipakai
                        Course.objects.for_listing()
                        Enrollment.objects.for_student_dashboard()

  Prinsip utama:
  ✅ Biarkan database yang menghitung (bukan Python)
  ✅ Ambil semua data relasi dalam 1-2 query (bukan N query)
  ✅ Gunakan annotate untuk COUNT/AVG yang terkait relasi
""")