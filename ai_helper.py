import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Ollama lokal
OLLAMA_MODEL = "qwen2.5:3b"

# Init OpenAI client jika API key tersedia
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================
# HELPER FORMAT
# =========================
def format_rupiah(value):
    try:
        return "Rp {:,}".format(int(value or 0)).replace(",", ".")
    except Exception:
        return "Rp 0"


def interpretasi_kol(kol):
    try:
        kol = int(kol)
    except Exception:
        return "Tidak terdeteksi"

    if kol == 1:
        return "Lancar"
    elif kol == 2:
        return "Dalam Perhatian Khusus"
    elif kol == 3:
        return "Kurang Lancar"
    elif kol == 4:
        return "Diragukan"
    elif kol == 5:
        return "Macet"

    return "Tidak terdeteksi"


# =========================
# PROMPT BUILDER
# =========================
def build_prompt(data):
    status_kol = interpretasi_kol(
        data.get("kolektibilitas_terburuk")
    )

    return f"""
Kamu adalah analis kredit internal bank di Indonesia.

Tugas kamu membuat CATATAN TAMBAHAN untuk membantu analis membaca data SLIK.
Catatan ini bukan keputusan kredit final.

GUNAKAN:
- Bahasa Indonesia formal
- Kalimat singkat
- Gaya faktual
- Format bullet point
- Maksimal 1 kalimat per bullet

JANGAN:
- terlalu banyak opini
- membuat asumsi kondisi usaha
- menyimpulkan gagal bayar
- memberi keputusan kredit final
- menggunakan bahasa promosi
- menggunakan bahasa motivasional
- menyebut kata "AI"
- membuat paragraf panjang
- mengulang semua data mentah

HINDARI KATA/KALIMAT:
- kemungkinan besar
- sangat baik
- luar biasa
- hebat
- cukup sehat
- debitur dipastikan
- debitur pasti
- layak disetujui
- wajib ditolak

GUNAKAN ISTILAH:
- terindikasi
- perlu diklarifikasi
- perlu diverifikasi
- menjadi perhatian analis
- berdasarkan data SLIK yang terbaca

PANDUAN KOLEKTIBILITAS:
- Kol 1 = Lancar
- Kol 2 = Dalam Perhatian Khusus
- Kol 3 = Kurang Lancar
- Kol 4 = Diragukan
- Kol 5 = Macet

ATURAN KOLEKTIBILITAS:
- Wajib mengikuti status kolektibilitas menurut sistem.
- Jangan menafsirkan ulang angka kolektibilitas.
- Jangan menyebut Kol 3, Kol 4, atau Kol 5 sebagai baik/lancar.
- Jangan menyebut debitur sehat jika terdapat Kol 3, Kol 4, atau Kol 5.
- Jangan menggunakan kalimat "kolektibilitas masih tinggi".
- Gunakan kalimat "riwayat kolektibilitas tinggi" atau "risiko kolektibilitas tinggi".

FORMAT OUTPUT WAJIB:

RINGKASAN PROFIL
- ...

ANALISIS RISIKO
- ...

CATATAN PENTING
- ...

REKOMENDASI / KLARIFIKASI
- ...

BATASAN OUTPUT:
- Setiap bagian maksimal 3 bullet.
- Setiap bullet maksimal 1 kalimat.
- Tidak perlu salam pembuka.
- Tidak perlu penutup panjang.
- Jangan gunakan markdown tebal.
- Jangan gunakan tabel.

DATA SLIK:

Nama Debitur: {data.get('nama', '-')}
NIK: {data.get('nik', '-')}
Posisi Data: {data.get('posisi_data', '-')}
Tanggal Permintaan: {data.get('tanggal_permintaan', '-')}

Kolektibilitas Terburuk: Kol {data.get('kolektibilitas_terburuk', '-')}
Status Kolektibilitas Menurut Sistem: {status_kol}
Periode Kolektibilitas Terburuk: {data.get('bulan_kolektibilitas_terburuk', '-')}

Jumlah Kreditur: {data.get('jumlah_kreditur', 0)}
Jumlah Fasilitas Terbaca: {data.get('jumlah_indikasi_fasilitas', 0)}
Fasilitas Aktif: {data.get('jumlah_fasilitas_aktif', data.get('jumlah_aktif', 0))}
Fasilitas Lunas: {data.get('jumlah_lunas', 0)}

Bank Umum: {data.get('bank_umum', 0)}
BPR/BPRS: {data.get('bpr_bprs', 0)}
Lembaga Pembiayaan: {data.get('lembaga_pembiayaan', 0)}

Total Plafon: {format_rupiah(data.get('total_plafon', 0))}
Total Baki Debet: {format_rupiah(data.get('total_baki_debet', 0))}
Total Tunggakan: {format_rupiah(data.get('total_tunggakan', 0))}

Jumlah Pinjol/Fintech: {data.get('jumlah_pinjol', 0)}
Fasilitas Baru 3 Bulan Terakhir: {data.get('jumlah_fasilitas_baru_3_bulan', 0)}
Pinjol/Fintech Baru 3 Bulan Terakhir: {data.get('jumlah_pinjol_baru_3_bulan', 0)}
"""


# =========================
# GENERATE OPENAI
# =========================
def generate_with_openai(prompt):
    if not client:
        raise Exception("OpenAI API key tidak tersedia")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah analis kredit internal bank Indonesia. "
                    "Gunakan Bahasa Indonesia formal, singkat, faktual, dan minim opini. "
                    "Jangan memberi keputusan kredit final."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# =========================
# GENERATE OLLAMA
# =========================
def generate_with_ollama(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        },
        timeout=120
    )

    response.raise_for_status()

    text = response.json().get("response", "")

    return clean_ai_text(text)


# =========================
# CLEAN OUTPUT
# =========================
def clean_ai_text(text):
    if not text:
        return ""

    text = text.replace("**", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")

    stop_keywords = [
        "BATASAN OUTPUT",
        "DATA SLIK",
        "GUNAKAN:",
        "JANGAN:",
        "HINDARI KATA",
        "PANDUAN KOLEKTIBILITAS",
        "ATURAN KOLEKTIBILITAS",
        "FORMAT OUTPUT WAJIB",
        "Tugas kamu",
        "Kamu adalah",
    ]

    allowed_headings = [
        "RINGKASAN PROFIL",
        "ANALISIS RISIKO",
        "CATATAN PENTING",
        "REKOMENDASI / KLARIFIKASI",
    ]

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        upper = line.upper()

        if any(keyword in upper for keyword in stop_keywords):
            continue

        if upper in allowed_headings:
            cleaned_lines.append(upper)
            continue

        if line.startswith("-"):
            cleaned_lines.append(line)
        elif line.startswith("•"):
            cleaned_lines.append("- " + line.lstrip("•").strip())
        else:
            if ":" in line and upper not in allowed_headings:
                cleaned_lines.append("- " + line)
            else:
                cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


# =========================
# MAIN FUNCTION
# =========================
def generate_ai_analysis(data):
    prompt = build_prompt(data)

    # 1. Coba OpenAI dulu
    try:
        result = generate_with_openai(prompt)
        return clean_ai_text(result)
    except Exception as e:
        print("OpenAI gagal → pakai Ollama:", e)

    # 2. Fallback ke Ollama lokal
    try:
        return generate_with_ollama(prompt)
    except Exception as e:
        print("Ollama gagal:", e)

    # 3. Semua gagal
    return None