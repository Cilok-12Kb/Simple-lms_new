# courses/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ── Endpoint Lab 5 ──────────────────────────────────────
    # Skenario 1: Course List + Teacher
    path('lab/course-list/baseline/',   views.course_list_baseline),
    path('lab/course-list/optimized/',  views.course_list_optimized),

    # Skenario 2: Course + Members + Konten + Komentar
    path('lab/course-members/baseline/',  views.course_members_baseline),
    path('lab/course-members/optimized/', views.course_members_optimized),

    # Skenario 3: Dashboard Statistik Dosen
    path('lab/course-dashboard/baseline/',  views.course_dashboard_baseline),
    path('lab/course-dashboard/optimized/', views.course_dashboard_optimized),

    # ── Bonus: Bulk Operations Demo ─────────────────────────
    path('lab/bulk-demo/', views.bulk_operations_demo),
]