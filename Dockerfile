# ─────────────────────────────────────────
# Base image: Python 3.11 versi slim
# "slim" artinya lebih kecil ukurannya,
# hanya berisi yang dibutuhkan saja
# ─────────────────────────────────────────
FROM python:3.11-slim

# Mencegah Python membuat file .pyc (bytecode cache)
# dan memaksa output langsung ke terminal (tidak di-buffer)
# Ini penting agar docker logs bisa ditampilkan real-time
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory di dalam container
# Semua perintah selanjutnya dijalankan dari /app
WORKDIR /app

# Install system dependencies yang dibutuhkan psycopg2
# postgresql-client: tools untuk koneksi ke PostgreSQL
# gcc: compiler C yang dibutuhkan beberapa library Python
# --no-install-recommends: jangan install package opsional (hemat space)
# rm -rf /var/lib/apt/lists/*: hapus cache apt setelah install (hemat space)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt DULU sebelum kode lain
# Ini trik penting untuk memanfaatkan Docker layer cache:
# Jika requirements.txt tidak berubah, Docker tidak perlu
# install ulang semua library (proses lama) saat rebuild
COPY requirements.txt .

# Install semua library Python
# --no-cache-dir: jangan simpan cache pip (hemat space)
RUN pip install --no-cache-dir -r requirements.txt

# Sekarang baru copy semua kode project ke /app
# Ini diletakkan terakhir karena kode paling sering berubah
COPY . .

# Dokumentasi: container ini akan menggunakan port 8000
# (ini hanya informasi, tidak membuka port — port dibuka di docker-compose)
EXPOSE 8000

# Perintah default saat container dijalankan
# Menjalankan Django development server yang mendengarkan di semua interface
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]