import sqlite3
from datetime import datetime
import json

DB_NAME = "database.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT,
                    username TEXT,
                    filename TEXT,
                    nama TEXT,
                    nik TEXT,
                    kolektibilitas TEXT,
                    bulan_kolektibilitas TEXT,
                    total_plafon INTEGER,
                    total_baki_debet INTEGER,
                    total_tunggakan INTEGER,
                    jumlah_kreditur INTEGER,
                    risiko TEXT,
                    rekomendasi TEXT,
                    ai_text TEXT,
                    extracted_json TEXT,
                    result_json TEXT
                )
            """)
            
            # Migrasi database jika kolom belum ada
            try:
                cursor.execute("ALTER TABLE history ADD COLUMN extracted_json TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE history ADD COLUMN result_json TEXT")
            except sqlite3.OperationalError:
                pass
    finally:
        conn.close()


def save_history(username, filename, extracted, result, ai_text):
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (
                    created_at, username, filename, nama, nik,
                    kolektibilitas, bulan_kolektibilitas,
                    total_plafon, total_baki_debet, total_tunggakan,
                    jumlah_kreditur, risiko, rekomendasi, ai_text,
                    extracted_json, result_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                username,
                filename,
                extracted.get("nama", ""),
                extracted.get("nik", ""),
                extracted.get("kolektibilitas_terburuk", ""),
                extracted.get("bulan_kolektibilitas_terburuk", ""),
                extracted.get("total_plafon", 0),
                extracted.get("total_baki_debet", 0),
                extracted.get("total_tunggakan", 0),
                extracted.get("jumlah_kreditur", 0),
                result.get("risk", ""),
                result.get("recommendation", ""),
                ai_text or "",
                json.dumps(extracted),
                json.dumps(result)
            ))
            return cursor.lastrowid
    finally:
        conn.close()


def get_history_by_id(history_id):
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM history WHERE id = ?", (history_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_history():
    conn = get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM history
            ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()
