import sqlite3
from datetime import datetime

DB_NAME = "database.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
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
            ai_text TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_history(username, filename, extracted, result, ai_text):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO history (
            created_at, username, filename, nama, nik,
            kolektibilitas, bulan_kolektibilitas,
            total_plafon, total_baki_debet, total_tunggakan,
            jumlah_kreditur, risiko, rekomendasi, ai_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ai_text or ""
    ))

    conn.commit()
    conn.close()


def get_history():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM history
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows