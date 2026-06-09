# Simple LMS — Backend Setup

**Nama:** Muhammad Ibadullah  
**NIM:** A11.2023.15275  
**Mata Kuliah:** Pemrograman Sisi Server  
**Universitas:** Dian Nuswantoro  

---

## Deskripsi

Setup environment development Django untuk Simple Learning Management System menggunakan Docker dan PostgreSQL, dilengkapi dengan data model LMS, query optimization, dan Django Admin interface.

## Tech Stack

| Teknologi | Versi | Fungsi |
|---|---|---|
| Python | 3.11 | Bahasa pemrograman |
| Django | 4.2.9 | Web framework |
| PostgreSQL | 15 | Database |
| Docker | Latest | Containerization |
| Docker Compose | v2 | Multi-container orchestration |
| Pillow | 10.2.0 | Image field support |

## Struktur Project

```
simple-lms/
├── docker-compose.yml        # Konfigurasi multi-container
├── Dockerfile                # Build image Django
├── .env.example              # Template environment variables
├── requirements.txt          # Python dependencies
├── manage.py                 # Django CLI tool
├── config/
│   ├── settings.py           # Konfigurasi Django
│   ├── urls.py               # URL routing
│   └── wsgi.py               # WSGI entry point
├── courses/                  # App utama LMS
│   ├── models.py             # Data models (User, Course, Lesson, dll)
│   ├── managers.py           # Custom QuerySet & Manager
│   ├── admin.py              # Konfigurasi Django Admin
│   └── migrations/           # File migrasi database
├── scripts/
│   ├── seed_data.py          # Script seed data awal
│   └── query_demo.py         # Demo N+1 problem & optimasi
└── fixtures/
    └── initial_data.json     # Data awal (hasil dumpdata)
```

## Data Models

### ERD Singkat

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

### Daftar Model

| Model | Deskripsi |
|---|---|
| `User` | Custom user dengan role: admin, instructor, student |
| `Category` | Kategori course, self-referencing untuk hierarki |
| `Course` | Course/mata kuliah dengan instructor dan kategori |
| `Lesson` | Pelajaran dalam course, memiliki field `order` untuk urutan |
| `Enrollment` | Pendaftaran siswa ke course, unique per student+course |
| `Progress` | Tracking penyelesaian lesson per enrollment |

## Custom Managers

| Manager | Method | Fungsi |
|---|---|---|
| `CourseManager` | `.for_listing()` | Query course dioptimasi untuk list view (select_related + annotate) |
| `CourseManager` | `.published()` | Hanya course yang sudah dipublikasikan |
| `EnrollmentManager` | `.for_student_dashboard(student)` | Enrollment + progress untuk dashboard siswa |

## Query Optimization

Project ini mengimplementasikan beberapa teknik optimasi query:

- **`select_related`** — untuk ForeignKey (SQL JOIN), mencegah N+1 pada `course.instructor`
- **`prefetch_related`** — untuk reverse FK, mencegah N+1 pada `course.lessons.all()`
- **`annotate(Count)`** — menghitung relasi di database, bukan di Python
- **`aggregate()`** — mengambil statistik (Max, Min, Avg) dalam 1 query
- **`bulk_create`** — insert banyak record sekaligus (1 query vs N query)

Hasil perbandingan (lihat `scripts/query_demo.py`):

| Operasi | Tanpa Optimasi | Dengan Optimasi |
|---|---|---|
| Course list + instructor | N+1 queries | 1 query (select_related) |
| Course + enrollment count | N+1 queries | 1 query (annotate) |
| Course + lessons | N+1 queries | 2 queries (prefetch_related) |

## Prerequisites

- Docker Desktop terinstall dan berjalan
- Port 8000 dan 5432 tidak digunakan aplikasi lain

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

### 6. Seed Data Awal (Opsional)

```bash
docker compose exec web python scripts/seed_data.py
```

### 7. Buka di Browser

- **Aplikasi:** http://localhost:8000
- **Admin:** http://localhost:8000/admin

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

## Screenshots

### Progres 1 — Django Welcome Page
![Progress 1](Screenshot/Progres_1/1.png)


---

*Progres 2 — Pemrograman Sisi Server, Universitas Dian Nuswantoro*