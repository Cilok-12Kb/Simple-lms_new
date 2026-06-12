# Simple LMS — Backend Setup

**Nama:** Muhammad Ibadullah  
**NIM:** A11.2023.15275  
**Mata Kuliah:** Pemrograman Sisi Server  
**Universitas:** Dian Nuswantoro  

---

## Deskripsi

Setup environment development Django untuk Simple Learning Management System menggunakan Docker dan PostgreSQL, dilengkapi dengan data model LMS, query optimization menggunakan Django Silk profiling, REST API dengan Django Ninja, serta JWT Authentication & Authorization dengan ninja-simple-jwt.

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
| django-ninja | 1.1.0 | REST API framework (Pydantic-based) |
| django-ninja-simple-jwt | 0.6.0 | JWT authentication dengan RSA keys |
| email-validator | 2.1.1 | Validasi format email di Pydantic |

## Struktur Project

```
simple-lms/
├── docker-compose.yml        # Konfigurasi multi-container
├── Dockerfile                # Build image Django
├── .env.example              # Template environment variables
├── requirements.txt          # Python dependencies
├── manage.py                 # Django CLI tool
├── postman_collection.json   # Postman collection untuk testing API
├── private_key.pem           # RSA private key (TIDAK di-commit ke Git)
├── public_key.pem            # RSA public key (TIDAK di-commit ke Git)
├── config/
│   ├── settings.py           # Konfigurasi Django + Silk + ninja-simple-jwt
│   ├── urls.py               # URL routing (/admin, /silk/, /api/)
│   └── wsgi.py               # WSGI entry point
├── courses/                  # App data model LMS
│   ├── models.py             # Data models (User, Course, Lesson, dll)
│   ├── managers.py           # Custom QuerySet & Manager
│   ├── admin.py              # Konfigurasi Django Admin
│   ├── views.py              # Endpoint baseline & optimized (Lab 5)
│   ├── urls.py               # Route endpoint lab
│   └── migrations/           # File migrasi database
├── api/                      # App REST API
│   ├── schemas.py            # Pydantic schemas (validasi input/output)
│   ├── helpers.py            # Helper functions untuk authorization checks
│   ├── main.py               # NinjaAPI instance + router registration
│   └── routers/
│       ├── auth_router.py    # /api/register/, /api/me/
│       ├── course_router.py  # /api/courses/* endpoints
│       └── enrollment_router.py  # /api/enrollments/* endpoints
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

| Kasus | Endpoint Baseline | Endpoint Optimized | Query Baseline | Query Optimized | Waktu Baseline | Waktu Optimized | Query Improvement | Waktu Improvement | Teknik |
|---|---|---|---|---|---|---|---|---|---|
| Course + Teacher | `/lab/course-list/baseline/` | `/lab/course-list/optimized/` | **101 queries** | **1 query** | 541ms | 39ms | **99%** | **93%** | `select_related` |
| Course + Members + Lessons | `/lab/course-members/baseline/` | `/lab/course-members/optimized/` | **301 queries** | **2 queries** | 2971ms | 60ms | **99%** | **98%** | `prefetch_related` + `annotate` |
| Statistik Dashboard | `/lab/course-dashboard/baseline/` | `/lab/course-dashboard/optimized/` | **203 queries** | **2 queries** | 1117ms | 36ms | **99%** | **97%** | `aggregate` + `annotate` |

> ✅ Semua endpoint optimized mencapai improvement **≥ 99%** (jauh melampaui target minimum 50%).

### Analisis N+1 Problem

#### Skenario 1 — Course List + Teacher (101 queries)
```
Baseline:  1 query (SELECT course) + 100 query (SELECT user WHERE id=?) = 101 queries
Optimized: 1 query JOIN (SELECT course.* INNER JOIN lms_user) = 1 query
```

#### Skenario 2 — Course + Members + Lessons (301 queries)
```
Baseline:  1 + 100 (instructor) + 100 (enrollment count) + 100 (lessons) = 301 queries
Optimized: 1 query (course+instructor JOIN) + 1 query (lessons prefetch) = 2 queries
```

#### Skenario 3 — Statistik Dashboard (203 queries)
```
Baseline:  1 + 100 (enrollment count loop) + 100 (instructor loop) + stats = 203 queries
Optimized: 1 query aggregate() + 1 query annotate() = 2 queries
```

### Screenshots Lab 5

#### Silk — Baseline Requests
![Silk Baseline](Screenshot/Silk/2.png)

#### Silk — Optimized Requests
![Silk Optimized](Screenshot/Silk/8.png)

---

## Progres 4 — REST API dengan Django Ninja

Membangun REST API menggunakan Django Ninja dengan Pydantic schemas dan Swagger UI.

### Daftar Endpoint API

#### Authentication

| Method | Endpoint | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/register/` | ❌ | Daftar user baru |
| POST | `/api/auth/sign-in` | ❌ | Login → dapat JWT tokens |
| POST | `/api/auth/token-refresh` | ❌ | Refresh access token |
| GET | `/api/me/` | ✅ | Ambil profil user login |
| PUT | `/api/me/` | ✅ | Update profil |

#### Courses

| Method | Endpoint | Auth | Deskripsi |
|---|---|---|---|
| GET | `/api/courses` | ❌ | List course (pagination + filter) |
| GET | `/api/courses/{id}` | ❌ | Detail course |
| POST | `/api/courses` | ✅ | Buat course (owner = user login) |
| PUT | `/api/courses/{id}` | ✅ | Update course (owner only) |
| DELETE | `/api/courses/{id}` | ✅ | Hapus course (owner/superadmin) |

#### Enrollments

| Method | Endpoint | Auth | Deskripsi |
|---|---|---|---|
| POST | `/api/enrollments` | ✅ | Daftar ke course |
| GET | `/api/enrollments/my-courses` | ✅ | Daftar course saya |
| POST | `/api/enrollments/{id}/progress` | ✅ | Tandai lesson selesai |

### Screenshots

#### Swagger UI — API Documentation
![Swagger UI](Screenshot/Progres_3/1.png)

---

## Progres 5 — Authentication & Authorization (Chapter 7)

Implementasi sistem authentication dan authorization yang aman menggunakan `ninja-simple-jwt` dengan RSA keys dan Role-Based Access Control (RBAC).

### Perubahan dari Progres 4

| Aspek | Progres 4 (PyJWT manual) | Progres 5 (ninja-simple-jwt) |
|---|---|---|
| Library | `PyJWT`, `passlib` | `django-ninja-simple-jwt` |
| Algoritma signing | HS256 (symmetric) | RSA (asymmetric, lebih aman) |
| Login endpoint | Ditulis manual | Otomatis dari `mobile_auth_router` |
| Key management | Secret key di `.env` | RSA key pair (`private_key.pem`, `public_key.pem`) |
| Token verification | Manual decode | Otomatis oleh `HttpJwtAuth` |

### Arsitektur Authentication

```
Client
  │
  ├─ POST /api/auth/sign-in ─────────────┐
  │                                      ▼
  │                           ninja-simple-jwt
  │                           verifikasi user
  │                           generate RSA-signed tokens
  │   { "access": "eyJ...", "refresh": "eyJ..." }
  │◄─────────────────────────────────────┘
  │
  ├─ GET /api/me/ ────────────────────────┐
  │   Authorization: Bearer <access>      │
  │                                       ▼
  │                             HttpJwtAuth.authenticate()
  │                             verify RSA signature
  │                             set request.user
  │   { "id": 1, "username": "..." }      │
  │◄──────────────────────────────────────┘
```

### Alur JWT (Chapter 7)

```
1. POST /api/auth/sign-in       → { "access": "...", "refresh": "..." }
2. Setiap request protected:    Authorization: Bearer <access_token>
3. HttpJwtAuth verifikasi RSA signature → set request.user
4. Access token expired         → POST /api/auth/token-refresh
5. Dapat access token baru tanpa login ulang
```

### Role-Based Access Control (RBAC)

| Role | Create Course | Edit Course | Delete Course | Enroll | Update Progress |
|---|---|---|---|---|---|
| Guest (tidak login) | ❌ 401 | ❌ 401 | ❌ 401 | ❌ 401 | ❌ 401 |
| Authenticated User | ✅ | ✅ (milik sendiri) | ✅ (milik sendiri) | ✅ | ✅ (milik sendiri) |
| Superadmin | ✅ | ✅ (semua) | ✅ (semua) | ✅ | ✅ |

Authorization diimplementasikan via **helper functions** di `api/helpers.py`:

```python
get_authenticated_user(request)        # ambil user dari token
check_course_owner(course, user)       # 403 jika bukan owner
check_owner_or_superadmin(owner, user) # 403 jika bukan owner/superadmin
check_enrollment(user, course)         # 403 jika tidak enrolled
```

### Matriks HTTP Status Code

| Endpoint | Tanpa Token | Token Valid | Pemilik/Superadmin |
|---|---|---|---|
| `GET /api/courses` | ✅ 200 | ✅ 200 | ✅ 200 |
| `POST /api/courses` | ❌ 401 | ✅ 201 | ✅ 201 |
| `PUT /api/courses/{id}` | ❌ 401 | ❌ 403 | ✅ 200 |
| `DELETE /api/courses/{id}` | ❌ 401 | ❌ 403 | ✅ 200 |
| `GET /api/me/` | ❌ 401 | ✅ 200 | ✅ 200 |
| `POST /api/enrollments` | ❌ 401 | ✅ 201 | ✅ 201 |

### HTTP Status Code Reference

| Kode | Nama | Kapan Dipakai |
|---|---|---|
| 200 | OK | Request berhasil |
| 201 | Created | Register berhasil, course dibuat |
| 400 | Bad Request | Duplikasi username/email, sudah enrolled |
| 401 | Unauthorized | Tidak ada token / token invalid / expired |
| 403 | Forbidden | Token valid tapi tidak punya izin |
| 404 | Not Found | Resource tidak ditemukan |

### Security Best Practices (Chapter 7 Section 8)

- **Password hashing** — `create_user()` bukan `create()` → PBKDF2+SHA256 otomatis
- **RSA asymmetric keys** — private key untuk sign, public key untuk verify
- **RSA keys di `.gitignore`** — `private_key.pem` tidak pernah di-commit
- **JWT payload minimal** — hanya `user_id`, tidak menyimpan password atau data sensitif
- **Token expiration** — access token pendek, refresh token lebih panjang
- **Input validation** — Pydantic Schema validasi otomatis, 422 jika format salah

### Testing 6 Skenario Wajib (Chapter 7)

| # | Skenario | Endpoint | Expected Result |
|---|---|---|---|
| 1 | Register user baru | `POST /api/register/` | 201 + data user (tanpa password) |
| 2 | Login dan dapat token | `POST /api/auth/sign-in` | 200 + access + refresh token |
| 3 | Akses dengan token valid | `GET /api/me/` | 200 + profil user |
| 4 | Akses tanpa token | `GET /api/me/` | 401 Unauthorized |
| 5 | Aksi yang diizinkan | `POST /api/courses` | 201 Created |
| 6 | Aksi yang ditolak | `PUT /api/courses/{id_milik_orang_lain}` | 403 Forbidden |


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
# Edit .env sesuai kebutuhan
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

### 5. Generate RSA Keys (sekali saja)

```bash
docker compose exec web python manage.py make_rsa
```

### 6. Buat Superuser

```bash
docker compose exec web python manage.py createsuperuser
```

### 7. Seed Data Awal

```bash
# Seed data standar
docker compose exec web python scripts/seed_data.py

# Seed data skala besar untuk Lab 5 (100+ courses)
docker compose exec web python scripts/seed_lab.py
```

### 8. Buka di Browser

| URL | Deskripsi |
|---|---|
| `http://localhost:8000/admin` | Django Admin |
| `http://localhost:8000/api/docs` | Swagger UI — REST API Documentation |
| `http://localhost:8000/silk/` | Django Silk profiling dashboard |
| `http://localhost:8000/lab/course-list/baseline/` | Endpoint baseline skenario 1 |
| `http://localhost:8000/lab/course-list/optimized/` | Endpoint optimized skenario 1 |
| `http://localhost:8000/lab/course-members/baseline/` | Endpoint baseline skenario 2 |
| `http://localhost:8000/lab/course-members/optimized/` | Endpoint optimized skenario 2 |
| `http://localhost:8000/lab/course-dashboard/baseline/` | Endpoint baseline skenario 3 |
| `http://localhost:8000/lab/course-dashboard/optimized/` | Endpoint optimized skenario 3 |

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

*Pemrograman Sisi Server — Universitas Dian Nuswantoro*