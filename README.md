# Simple LMS — Backend Setup

**Nama:** Muhammad Ibadullah  
**NIM:** A11.2023.15275  
**Mata Kuliah:** Pemrograman Sisi Server  
**Universitas:** Dian Nuswantoro  

---

## Deskripsi

Setup environment development Django untuk Simple Learning Management System menggunakan Docker dan PostgreSQL, dilengkapi dengan data model LMS, query optimization menggunakan Django Silk profiling, dan Django Admin interface.

## Tech Stack

| Teknologi | Versi | Fungsi |
|---|---|---|
| Python | 3.11 | Bahasa pemrograman |
| Django | 4.2.9 | Web framework |
| PostgreSQL | 15 | Database |
| Docker | Latest | Containerization |
| Docker Compose | v2 | Multi-container orchestration |
| Pillow | 10.2.0 | Image field support |
| django-silk | 5.0.3 | Query profiling & benchmarking |

## Struktur Project

```
simple-lms/
├── docker-compose.yml        # Konfigurasi multi-container
├── Dockerfile                # Build image Django
├── .env.example              # Template environment variables
├── requirements.txt          # Python dependencies
├── manage.py                 # Django CLI tool
├── config/
│   ├── settings.py           # Konfigurasi Django + Silk middleware
│   ├── urls.py               # URL routing (termasuk /silk/)
│   └── wsgi.py               # WSGI entry point
├── courses/                  # App utama LMS
│   ├── models.py             # Data models (User, Course, Lesson, dll)
│   ├── managers.py           # Custom QuerySet & Manager
│   ├── admin.py              # Konfigurasi Django Admin
│   ├── views.py              # Endpoint baseline & optimized (Lab 5)
│   ├── urls.py               # Route endpoint lab
│   └── migrations/           # File migrasi database
├── scripts/
│   ├── seed_data.py          # Script seed data awal
│   ├── seed_lab.py           # Script seed data skala besar (100+ course)
│   └── query_demo.py         # Demo N+1 problem & optimasi
└── fixtures/
    └── initial_data.json     # Data awal (hasil dumpdata)
```

---

## Progres 1 — Docker + Django + PostgreSQL Setup

Setup environment development Django dengan Docker Compose dan PostgreSQL sebagai database.

### Yang Dikerjakan

- Membuat `Dockerfile` untuk build image Django custom
- Konfigurasi `docker-compose.yml` dengan service `web` (Django) dan `db` (PostgreSQL)
- Setup `settings.py` dengan `python-decouple` untuk environment variables
- Konfigurasi koneksi PostgreSQL menggantikan SQLite default
- Static files configuration

### Screenshots

#### Django Welcome Page
![Progress 1](Screenshot/Progres_1/1.png)

---

## Progres 2 — Django ORM & Data Models

Implementasi data model untuk Simple LMS menggunakan Django ORM dengan relasi yang tepat dan optimasi query.

### Data Models

#### ERD

```
User (role: admin/instructor/student)
 │
 ├──[FK instructor]── Course ──[FK category]── Category (self-referencing)
 │                      │
 │                 ──[FK course]── Lesson (dengan field order)
 │
 └──[FK student, via Enrollment]── Course
              │
         Enrollment (unique: student+course)
              │
         Progress (tracking per-lesson)
```

#### Daftar Model

| Model | Deskripsi |
|---|---|
| `User` | Custom user extends AbstractUser, role: admin/instructor/student |
| `Category` | Kategori course dengan self-referencing FK untuk hierarki |
| `Course` | Course/mata kuliah dengan instructor, category, level, price |
| `Lesson` | Pelajaran dalam course, field `order` untuk urutan tampil |
| `Enrollment` | Pendaftaran siswa ke course, `unique_together` (student+course) |
| `Progress` | Tracking penyelesaian lesson per enrollment |

### Custom Managers

| Manager | Method | Fungsi |
|---|---|---|
| `CourseManager` | `.for_listing()` | Course list dioptimasi: `select_related` + `annotate` |
| `CourseManager` | `.published()` | Filter hanya course `is_published=True` |
| `EnrollmentManager` | `.for_student_dashboard(student)` | Dashboard siswa dengan `prefetch_related` progress |

### Database Indexes

Index ditambahkan pada kolom yang sering dipakai untuk `filter()` dan `order_by()`:

| Index | Model | Kolom | Alasan |
|---|---|---|---|
| `idx_course_slug` | Course | `slug` | Lookup by slug di URL routing |
| `idx_course_pub_date` | Course | `is_published, -created_at` | Filter published + sort terbaru |
| `idx_course_price` | Course | `price` | Filter/sort harga di dashboard |
| `idx_course_inst_pub` | Course | `instructor, is_published` | Dashboard dosen: course published milik instructor X |
| `idx_course_level` | Course | `level` | Filter berdasarkan level |
| `idx_enroll_student_status` | Enrollment | `student, status` | Dashboard siswa: enrollment aktif |
| `idx_enroll_course_status` | Enrollment | `course, status` | Statistik enrollment per course |

---

## Progres 3 (Lab 5) — Optimasi Database dengan Django Silk

Profiling dan optimasi 3 endpoint menggunakan Django Silk. Membuktikan N+1 problem dan solusinya secara terukur.

### Endpoint Lab

| Endpoint | Deskripsi |
|---|---|
| `GET /lab/course-list/baseline/` | Daftar course + instructor — belum dioptimasi |
| `GET /lab/course-list/optimized/` | Daftar course + instructor — `select_related` |
| `GET /lab/course-members/baseline/` | Course + members + lessons — belum dioptimasi |
| `GET /lab/course-members/optimized/` | Course + members + lessons — `prefetch_related` + `annotate` |
| `GET /lab/course-dashboard/baseline/` | Statistik dashboard — belum dioptimasi |
| `GET /lab/course-dashboard/optimized/` | Statistik dashboard — `aggregate` + `annotate` |
| `GET /silk/` | Dashboard profiling Django Silk |

### Hasil Perbandingan Silk

Data diukur langsung dari Django Silk dengan dataset 100+ courses.

| Kasus | Endpoint Baseline | Endpoint Optimized | Query Baseline | Query Optimized | Waktu Baseline | Waktu Optimized | Query Improvement | Waktu Improvement | Teknik |
|---|---|---|---|---|---|---|---|---|---|
| Course + Teacher | `/lab/course-list/baseline/` | `/lab/course-list/optimized/` | **101 queries** | **1 query** | 541ms | 39ms | **99%** | **93%** | `select_related` |
| Course + Members + Lessons | `/lab/course-members/baseline/` | `/lab/course-members/optimized/` | **301 queries** | **2 queries** | 2971ms | 60ms | **99%** | **98%** | `prefetch_related` + `annotate` |
| Statistik Dashboard | `/lab/course-dashboard/baseline/` | `/lab/course-dashboard/optimized/` | **203 queries** | **2 queries** | 1117ms | 36ms | **99%** | **97%** | `aggregate` + `annotate` |

> ✅ Semua endpoint optimized mencapai improvement **≥ 99%** (jauh melampaui target minimum 50%).

### Analisis N+1 Problem

#### Skenario 1 — Course List + Teacher (101 queries)

```
Baseline:
  courses = Course.objects.all()           → 1 query (SELECT * FROM lms_course)
  for course in courses:
      course.instructor.username           → 1 query PER COURSE (SELECT * FROM lms_user WHERE id=?)
                                           → 100 courses = 100 query tambahan
  Total: 1 + 100 = 101 queries

Optimized:
  courses = Course.objects.select_related('instructor').all()
  → 1 query JOIN (SELECT course.*, user.* FROM lms_course INNER JOIN lms_user ...)
  Total: 1 query
```

#### Skenario 2 — Course + Members + Lessons (301 queries)

```
Baseline:
  1 query   : ambil semua course
  100 query : course.instructor per course     (N+1)
  100 query : Enrollment.filter(course=c)      (N+1)
  100 query : Lesson.filter(course=c)          (N+1)
  Total: 1 + 300 = 301 queries

Optimized:
  1 query : course + instructor (select_related JOIN)
  1 query : semua lessons (prefetch_related IN clause)
  + annotate enrollment_count di query pertama
  Total: 2 queries
```

#### Skenario 3 — Statistik Dashboard (203 queries)

```
Baseline:
  1 query   : ambil semua course
  100 query : Enrollment.filter(course=c).count() per course   (N+1)
  100 query : course.instructor per course                      (N+1)
  + beberapa query statistik terpisah
  Total: 203 queries

Optimized:
  1 query : aggregate() → COUNT, MAX, MIN, AVG sekaligus
  1 query : courses + annotate(enrollment_count) + select_related(instructor)
  Total: 2 queries
```

### Teknik Optimasi yang Digunakan

| Teknik | Kapan Dipakai | Contoh |
|---|---|---|
| `select_related` | ForeignKey (many-to-one) | `Course → instructor` |
| `prefetch_related` | Reverse FK / ManyToMany | `Course → lessons` |
| `annotate(Count)` | Hitung relasi di database | Jumlah enrollment per course |
| `aggregate()` | Statistik global | MAX, MIN, AVG, COUNT sekaligus |
| `bulk_create` | Insert banyak record | Seed 100 course dalam 1 query |
| `QuerySet.update(F())` | Update massal | Naikkan harga semua course |

### Screenshots Lab 5

#### Silk — Baseline Requests
![Silk Baseline](Screenshot/Lab5/silk_baseline.png)

#### Silk — Optimized Requests (Perbandingan)
![Silk Optimized](Screenshot/Lab5/silk_optimized.png)

---

## Prerequisites

- Docker Desktop terinstall dan berjalan
- Port 8000 tidak digunakan aplikasi lain

## Cara Menjalankan

### 1. Clone Repository

```bash
git clone [URL_REPO_KAMU]
cd simple-lms
```

### 2. Setup Environment Variables

```bash
cp .env.example .env
# Edit .env sesuai kebutuhan (terutama SECRET_KEY dan password)
```

### 3. Jalankan Docker Compose

```bash
docker compose up -d
```

### 4. Jalankan Migrasi Database

```bash
docker compose exec web python manage.py makemigrations courses
docker compose exec web python manage.py migrate
```

### 5. Buat Superuser

```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Seed Data Awal

```bash
# Seed data standar
docker compose exec web python scripts/seed_data.py

# Seed data skala besar untuk Lab 5 (100+ courses)
docker compose exec web python scripts/seed_lab.py
```

### 7. Buka di Browser

| URL | Deskripsi |
|---|---|
| http://localhost:8000/admin | Django Admin |
| http://localhost:8000/silk/ | Django Silk profiling dashboard |
| http://localhost:8000/lab/course-list/baseline/ | Endpoint baseline skenario 1 |
| http://localhost:8000/lab/course-list/optimized/ | Endpoint optimized skenario 1 |
| http://localhost:8000/lab/course-members/baseline/ | Endpoint baseline skenario 2 |
| http://localhost:8000/lab/course-members/optimized/ | Endpoint optimized skenario 2 |
| http://localhost:8000/lab/course-dashboard/baseline/ | Endpoint baseline skenario 3 |
| http://localhost:8000/lab/course-dashboard/optimized/ | Endpoint optimized skenario 3 |

### Perintah Berguna

```bash
# Lihat status container
docker compose ps

# Lihat logs
docker compose logs -f web

# Masuk ke shell Django
docker compose exec web python manage.py shell

# Jalankan demo query optimization
docker compose exec web python scripts/query_demo.py

# Export data ke fixture
docker compose exec web python manage.py dumpdata courses --indent 2 -o fixtures/initial_data.json

# Stop semua service
docker compose down

# Stop dan hapus data (HATI-HATI!)
docker compose down -v
```

## Environment Variables

| Variabel | Fungsi | Contoh |
|---|---|---|
| `SECRET_KEY` | Kunci enkripsi Django | string acak panjang |
| `DEBUG` | Mode debug | `True` (dev) / `False` (prod) |
| `ALLOWED_HOSTS` | Host yang diizinkan | `localhost,127.0.0.1` |
| `DB_NAME` | Nama database PostgreSQL | `lms_db` |
| `DB_USER` | Username database | `lms_user` |
| `DB_PASSWORD` | Password database | string kuat |
| `DB_HOST` | Hostname database | `db` (nama service Docker) |
| `DB_PORT` | Port database | `5432` |

---

*Latihan Optimisasi DB — Universitas Dian Nuswantoro*