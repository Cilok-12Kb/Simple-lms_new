# Simple LMS — Backend Setup

**Nama:** Muhammad Ibadullah  
**NIM:** A11.2023.15275  
**Mata Kuliah:** Pemrograman Sisi Server  
**Universitas:** Dian Nuswantoro  

---

## Deskripsi

Setup environment development Django untuk Simple Learning Management System
menggunakan Docker dan PostgreSQL.

## Tech Stack

| Teknologi | Versi | Fungsi |
|---|---|---|
| Python | 3.11 | Bahasa pemrograman |
| Django | 4.2.9 | Web framework |
| PostgreSQL | 15 | Database |
| Docker | Latest | Containerization |
| Docker Compose | v2 | Multi-container orchestration |

## Struktur Project
simple-lms/
├── docker-compose.yml    # Konfigurasi multi-container
├── Dockerfile            # Build image Django
├── .env.example          # Template environment variables
├── requirements.txt      # Python dependencies
├── manage.py             # Django CLI tool
└── config/
├── settings.py       # Konfigurasi Django
├── urls.py           # URL routing
└── wsgi.py           # WSGI entry point

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
docker compose exec web python manage.py migrate
```

### 5. Buka di Browser
http://localhost:8000

### Perintah Berguna

```bash
# Lihat status container
docker compose ps

# Lihat logs
docker compose logs -f web

# Masuk ke shell Django
docker compose exec web python manage.py shell

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

### Django Welcome Page
![Progress 1](Screenshot/Progres_1/1.png)

---

*Progres_1 — Pemrograman Sisi Server, Universitas Dian Nuswantoro*