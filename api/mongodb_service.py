"""
api/mongodb_service.py
Service layer untuk MongoDB — Activity Logs & Analytics.
Sesuai Chapter 12: MongoDB Integration.
"""
from pymongo import MongoClient, DESCENDING
from datetime import datetime
from django.conf import settings
from typing import Optional


def get_db():
    """Koneksi ke MongoDB database lms_analytics."""
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB]


# ─────────────────────────────────────────────────────────────
# ACTIVITY LOG COLLECTION
# ─────────────────────────────────────────────────────────────

def log_activity(user_id: int, action: str, course_name: str = None,
                 metadata: dict = None) -> str:
    """
    Catat aktivitas user ke MongoDB activity_logs collection.

    Sesuai Chapter 12 Section 7.1: schema embedding untuk metadata.
    """
    db = get_db()
    doc = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.utcnow(),
    }
    if course_name:
        doc["course_name"] = course_name
    if metadata:
        doc["metadata"] = metadata

    result = db.activity_logs.insert_one(doc)
    return str(result.inserted_id)


def get_user_activity(user_id: int, limit: int = 10) -> list:
    """Ambil 10 aktivitas terbaru user."""
    db = get_db()
    logs = list(
        db.activity_logs
        .find({"user_id": user_id}, {"_id": 0})
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    # Konversi datetime ke string untuk JSON
    for log in logs:
        if "timestamp" in log:
            log["timestamp"] = log["timestamp"].isoformat()
    return logs


# ─────────────────────────────────────────────────────────────
# LEARNING ANALYTICS — Aggregation Pipeline (Chapter 12 Section 5)
# ─────────────────────────────────────────────────────────────

def get_popular_courses(limit: int = 5) -> list:
    """
    Top N course terpopuler berdasarkan views.
    Menggunakan aggregation pipeline (Chapter 12 Section 5.3).
    """
    db = get_db()
    pipeline = [
        {"$match": {"action": "view_course"}},
        {"$group": {
            "_id": "$course_name",
            "total_views": {"$sum": 1},
            "unique_users": {"$addToSet": "$user_id"},
        }},
        {"$addFields": {
            "unique_user_count": {"$size": "$unique_users"}
        }},
        {"$sort": {"total_views": -1}},
        {"$limit": limit},
        {"$project": {
            "course": "$_id",
            "total_views": 1,
            "unique_user_count": 1,
            "_id": 0,
        }}
    ]
    return list(db.activity_logs.aggregate(pipeline))


def get_daily_summary(days: int = 7) -> list:
    """Ringkasan aktivitas harian (N hari terakhir)."""
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "total_actions": {"$sum": 1},
            "unique_users": {"$addToSet": "$user_id"},
        }},
        {"$addFields": {
            "unique_user_count": {"$size": "$unique_users"}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": days},
        {"$project": {
            "date": "$_id",
            "total_actions": 1,
            "unique_user_count": 1,
            "_id": 0,
        }}
    ]
    return list(db.activity_logs.aggregate(pipeline))


def save_course_statistics(stats: dict) -> str:
    """Simpan statistik course ke MongoDB (dipanggil oleh Celery task)."""
    db = get_db()
    stats["saved_at"] = datetime.utcnow()
    result = db.course_statistics.insert_one(stats)
    return str(result.inserted_id)


def setup_indexes():
    """
    Buat indexes yang diperlukan (Chapter 12 Section 9).
    Panggil sekali saat startup atau via management command.
    """
    db = get_db()
    # Index untuk query aktivitas per user
    db.activity_logs.create_index([("user_id", 1), ("timestamp", -1)])
    # Index untuk filter berdasarkan action
    db.activity_logs.create_index([("action", 1)])
    # TTL index: hapus log lebih dari 90 hari otomatis
    db.activity_logs.create_index(
        [("timestamp", 1)],
        expireAfterSeconds=7776000  # 90 hari
    )