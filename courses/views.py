"""
courses/views.py
Endpoint untuk Lab Praktikum 5: Optimasi Database
Berisi 3 pasangan endpoint: baseline (jelek) vs optimized (bagus)
"""
from django.http import JsonResponse
from django.db.models import Count, Avg, Max, Min, Sum, Q, Prefetch
from django.contrib.auth import get_user_model

from .models import Course, Lesson, Enrollment

User = get_user_model()


# ═══════════════════════════════════════════════════════════════
# SKENARIO 1: DAFTAR COURSE + TEACHER
# ═══════════════════════════════════════════════════════════════

def course_list_baseline(request):
    """
    ❌ BASELINE — N+1 Problem.
    
    Query yang terjadi:
    - 1 query: SELECT * FROM lms_course
    - N query: SELECT * FROM lms_user WHERE id = ? (satu per course!)
    
    Untuk 100 course = 101 queries!
    """
    courses = Course.objects.all()   # 1 query, ambil semua course
    data = []
    for course in courses:
        data.append({
            'id': course.id,
            'title': course.title,
            # ↓ Ini menyebabkan N+1 — setiap akses .instructor = 1 query baru!
            'instructor': course.instructor.get_full_name(),
            'instructor_username': course.instructor.username,
            'level': course.level,
            'price': str(course.price),
        })
    return JsonResponse({'data': data, 'count': len(data)})


def course_list_optimized(request):
    """
    ✅ OPTIMIZED — select_related (SQL JOIN).
    
    Query yang terjadi:
    - 1 query: SELECT course.*, user.* FROM lms_course
               INNER JOIN lms_user ON course.instructor_id = user.id
    
    Untuk 100 course = TETAP 1 query!
    """
    courses = Course.objects.select_related('instructor').all()
    data = []
    for course in courses:
        data.append({
            'id': course.id,
            'title': course.title,
            # ↓ Tidak ada query tambahan — data instructor sudah di-JOIN
            'instructor': course.instructor.get_full_name(),
            'instructor_username': course.instructor.username,
            'level': course.level,
            'price': str(course.price),
        })
    return JsonResponse({'data': data, 'count': len(data)})


# ═══════════════════════════════════════════════════════════════
# SKENARIO 2: DAFTAR COURSE + MEMBERS + KONTEN + KOMENTAR
# ═══════════════════════════════════════════════════════════════

def course_members_baseline(request):
    """
    ❌ BASELINE — N+1 berlapis.
    
    Query yang terjadi untuk 50 course, masing-masing 5 lessons:
    - 1 query: ambil semua course
    - 50 query: ambil instructor per course       (N)
    - 50 query: hitung enrollment per course      (N)
    - 50 query: ambil lessons per course          (N)
    - 250 query: hitung progress per lesson       (N*M)
    
    Total: 1 + 50 + 50 + 50 + 250 = 401 queries!
    """
    courses = Course.objects.all()
    data = []
    for course in courses:
        # Setiap baris di bawah = query terpisah ke database!
        enrollment_count = Enrollment.objects.filter(course=course).count()
        lessons = Lesson.objects.filter(course=course)
        lesson_list = []
        for lesson in lessons:
            lesson_list.append({
                'title': lesson.title,
                'type': lesson.content_type,
                'duration': lesson.duration_minutes,
            })
        data.append({
            'id': course.id,
            'title': course.title,
            'instructor': course.instructor.username,    # N+1
            'enrollments': enrollment_count,            # N+1
            'lesson_count': len(lesson_list),           # N+1
            'lessons': lesson_list[:3],                 # N+1 berlapis
        })
    return JsonResponse({'data': data, 'count': len(data)})


def course_members_optimized(request):
    """
    ✅ OPTIMIZED — select_related + prefetch_related + annotate.
    
    Query yang terjadi:
    - 1 query: course + instructor (JOIN via select_related)
    - 1 query: semua lessons untuk semua courses (prefetch IN clause)
    - 1 query: annotate enrollment_count (COUNT di database)
    
    Total: 3 queries, untuk berapapun jumlah course!
    """
    courses = Course.objects.select_related(
        'instructor',           # ForeignKey → JOIN
    ).prefetch_related(
        'lessons',              # Reverse FK → 1 query terpisah dengan IN clause
    ).annotate(
        enrollment_count=Count('enrollments', distinct=True),  # Hitung di DB
    ).all()

    data = []
    for course in courses:
        lesson_list = []
        for lesson in course.lessons.all():     # Dari prefetch_related, TIDAK query baru
            lesson_list.append({
                'title': lesson.title,
                'type': lesson.content_type,
                'duration': lesson.duration_minutes,
            })
        data.append({
            'id': course.id,
            'title': course.title,
            'instructor': course.instructor.username,     # Dari select_related
            'enrollments': course.enrollment_count,      # Dari annotate
            'lesson_count': len(lesson_list),
            'lessons': lesson_list[:3],                  # Sudah di-prefetch
        })
    return JsonResponse({'data': data, 'count': len(data)})


# ═══════════════════════════════════════════════════════════════
# SKENARIO 3: STATISTIK DASHBOARD DOSEN
# ═══════════════════════════════════════════════════════════════

def course_dashboard_baseline(request):
    """
    ❌ BASELINE — Statistik dihitung di Python dengan banyak query terpisah.
    
    Query yang terjadi:
    - 1 query: ambil semua course
    - N query: hitung enrollment per course dalam loop
    - 1 query: total course
    - 1 query: total enrollment
    - 1 query: max price
    - 1 query: min price
    - 1 query: avg price
    - 1 query: top course (sorted)
    
    Total: 1 + N + 6 = N+7 queries!
    """
    courses = Course.objects.all()

    # Dihitung satu per satu dalam Python — SANGAT TIDAK EFISIEN
    total_enrollments = 0
    course_stats = []
    for course in courses:
        # Setiap ini = 1 query ke database!
        count = Enrollment.objects.filter(course=course).count()
        total_enrollments += count
        course_stats.append({
            'title': course.title,
            'instructor': course.instructor.username,  # N+1 lagi!
            'price': str(course.price),
            'enrollments': count,
        })

    # Statistik global — masing-masing 1 query terpisah!
    total_courses = Course.objects.count()
    all_prices = list(Course.objects.values_list('price', flat=True))
    max_price = max(all_prices) if all_prices else 0
    min_price = min(all_prices) if all_prices else 0
    avg_price = sum(all_prices) / len(all_prices) if all_prices else 0

    return JsonResponse({
        'summary': {
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'max_price': str(max_price),
            'min_price': str(min_price),
            'avg_price': str(round(avg_price, 2)),
        },
        'courses': course_stats[:10],
    })


def course_dashboard_optimized(request):
    """
    ✅ OPTIMIZED — aggregate() + annotate() untuk semua kalkulasi di database.
    
    Query yang terjadi:
    - 1 query: aggregate() untuk semua statistik global sekaligus
    - 1 query: courses + enrollment_count + lesson_count (annotate + select_related)
    
    Total: 2 queries, untuk berapapun jumlah course!
    
    SQL yang dihasilkan aggregate():
    SELECT COUNT(id), MAX(price), MIN(price), AVG(price), SUM(price)
    FROM lms_course;   ← Satu query!
    """
    # Semua statistik global dalam 1 query
    stats = Course.objects.aggregate(
        total_courses=Count('id'),
        max_price=Max('price'),
        min_price=Min('price'),
        avg_price=Avg('price'),
        total_revenue=Sum('price'),
    )

    # Course dengan data relasi + kalkulasi, semua dalam 1 query
    courses = Course.objects.select_related(
        'instructor'
    ).annotate(
        enrollment_count=Count('enrollments', distinct=True),
        lesson_count=Count('lessons', distinct=True),
        # Hitung student dan instructor enrollment secara conditional
        active_enrollments=Count(
            'enrollments',
            filter=Q(enrollments__status='active'),
            distinct=True,
        ),
    ).order_by('-enrollment_count')

    course_list = []
    for course in courses[:10]:
        course_list.append({
            'title': course.title,
            'instructor': course.instructor.username,     # Dari select_related
            'price': str(course.price),
            'enrollments': course.enrollment_count,      # Dari annotate
            'active_enrollments': course.active_enrollments,
            'lesson_count': course.lesson_count,         # Dari annotate
        })

    return JsonResponse({
        'summary': {
            'total_courses': stats['total_courses'],
            'max_price': str(stats['max_price'] or 0),
            'min_price': str(stats['min_price'] or 0),
            'avg_price': str(round(stats['avg_price'] or 0, 2)),
            'total_revenue': str(stats['total_revenue'] or 0),
        },
        'top_courses': course_list,
    })


# ═══════════════════════════════════════════════════════════════
# BONUS: BULK OPERATIONS DEMO
# ═══════════════════════════════════════════════════════════════

def bulk_operations_demo(request):
    """
    Demo bulk_create dan QuerySet.update() vs individual save().
    Endpoint ini mendemonstrasikan perbedaan performa operasi massal.
    """
    import time
    from django.db import connection, reset_queries
    from django.conf import settings
    from django.db.models import F
    from .models import Category

    results = {}
    settings.DEBUG = True

    # ── Demo 1: Bulk update price ────────────────────────────
    # Update semua course: naikkan harga 10% menggunakan F() expression
    # 1 query SQL UPDATE untuk semua record!
    reset_queries()
    start = time.perf_counter()
    updated_count = Course.objects.filter(
        price__gt=0
    ).update(price=F('price') * 1)  # x1 agar tidak benar-benar berubah
    elapsed = (time.perf_counter() - start) * 1000

    results['bulk_update'] = {
        'method': 'QuerySet.update(F expression)',
        'records_affected': updated_count,
        'queries': len(connection.queries),
        'time_ms': round(elapsed, 2),
        'note': 'Satu query UPDATE untuk semua record sekaligus',
    }

    # ── Demo 2: Aggregate statistik ──────────────────────────
    reset_queries()
    start = time.perf_counter()
    stats = Course.objects.aggregate(
        total=Count('id'),
        avg=Avg('price'),
        max_val=Max('price'),
        min_val=Min('price'),
    )
    elapsed = (time.perf_counter() - start) * 1000

    results['aggregate'] = {
        'method': 'aggregate() gabungan',
        'queries': len(connection.queries),
        'time_ms': round(elapsed, 2),
        'stats': {k: str(v) for k, v in stats.items()},
        'note': 'COUNT, AVG, MAX, MIN dalam 1 query',
    }

    return JsonResponse({
        'demo_results': results,
        'message': 'Lihat tab SQL di Django Silk untuk detail query',
    })