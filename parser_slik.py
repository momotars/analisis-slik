import os
import re
import pandas as pd
import pdfplumber
from datetime import datetime


# =========================
# UTIL
# =========================

BULAN_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

PINJOL_KEYWORDS = [
    "lentera dana", "pendanaan", "teknologi finansial", "trust teknologi",
    "pintar inovasi", "modal rakyat", "progo puncak", "mapan global",
    "dana nusantara", "cakrawala citra", "fintech", "pinjam",
    "kredit pintar", "seabank", "allo bank", "bank jago",
    "krom bank", "neo commerce", "uob", "dbs",
]

LEMBAGA_PEMBIAYAAN_KEYWORDS = [
    "finance", "multifinance", "pembiayaan", "leasing",
    "adira", "fif", "baf", "wom", "mega finance",
    "oto", "summit", "mandiri utama finance",
]


def normalize_text(text):
    text = text or ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def parse_rupiah(value):
    if not value:
        return 0

    value = str(value)
    value = value.replace("Rp", "")
    value = value.replace(" ", "")

    if "," in value:
        value = value.split(",")[0]

    value = re.sub(r"[^0-9]", "", value)
    return int(value) if value else 0


def format_rupiah(value):
    try:
        return f"{int(value or 0):,}".replace(",", ".")
    except Exception:
        return "0"


def find_first(pattern, text, default=""):
    match = re.search(pattern, text or "", re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return default


def safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def clean_name(value):
    if not value:
        return ""

    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace("Nama Sesuai Identitas", "")
    value = value.replace("Nama", "")
    value = value.replace("NIK /", "")
    value = value.replace("NIK", "")

    return value.strip()


def clean_kreditur(value):
    if not value:
        return ""

    value = re.sub(r"^\d{3,6}\s+-\s+", "", value)
    value = re.sub(r"\s+", " ", value).strip()

    value = re.sub(r"Rp\s*[\d\.,]+.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"Kualitas.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"Pelapor.*$", "", value, flags=re.IGNORECASE)

    bulan_pattern = r"\b(Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agt|Sep|Okt|Nov|Des)\s+\d{2}\b"
    value = re.split(bulan_pattern, value)[0].strip()

    stop_words = [
        " Kantor Pusat",
        " KC ",
        " KCP ",
        " KPO ",
        " Cabang ",
    ]

    for stop in stop_words:
        idx = value.find(stop)
        if idx > 8:
            value = value[:idx].strip()
            break

    return value.strip(" -/")


def parse_tanggal_id(tanggal_text):
    if not tanggal_text:
        return None

    tanggal_text = tanggal_text.strip().lower()
    tanggal_text = re.sub(r"\s+", " ", tanggal_text)

    parts = tanggal_text.split(" ")

    try:
        if len(parts) == 3:
            hari = int(parts[0])
            bulan = BULAN_ID.get(parts[1])
            tahun = int(parts[2])

            if bulan:
                return datetime(tahun, bulan, hari)

        if len(parts) == 2:
            bulan = BULAN_ID.get(parts[0])
            tahun = int(parts[1])

            if bulan:
                return datetime(tahun, bulan, 1)

    except Exception:
        return None

    return None


def month_diff(start_date, end_date):
    if not start_date or not end_date:
        return None

    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)


def is_pinjol_provider(kreditur, jenis=""):
    text = f"{kreditur} {jenis}".lower()
    return any(keyword in text for keyword in PINJOL_KEYWORDS)


def kategori_kreditur(kreditur):
    nama_lower = (kreditur or "").lower()

    # BPR/BPRS harus dicek dulu sebelum keyword "bank"
    if (
        "bprs" in nama_lower
        or "bpr" in nama_lower
        or "bank perekonomian rakyat" in nama_lower
        or "bank perkreditan rakyat" in nama_lower
    ):
        return "BPR/BPRS"

    if "bank" in nama_lower:
        return "BANK UMUM"

    if any(keyword in nama_lower for keyword in LEMBAGA_PEMBIAYAAN_KEYWORDS):
        return "LEMBAGA PEMBIAYAAN"

    return "LAINNYA"


# =========================
# READ FILE
# =========================

def parse_pdf(filepath):
    text_all = ""

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            text_all += "\n" + text

    return extract_basic_fields(text_all)


def parse_excel(filepath):
    sheets = pd.read_excel(filepath, sheet_name=None, dtype=str)
    combined_text = ""

    for sheet_name, df in sheets.items():
        combined_text += f"\n--- SHEET: {sheet_name} ---\n"
        combined_text += df.fillna("").to_string(index=False)

    return extract_basic_fields(combined_text)


# =========================
# DETAIL KREDIT
# =========================

def extract_kredit_blocks(text):
    parts = re.split(r"(?=\d{3,6}\s+-\s+)", text or "")
    blocks = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if not re.match(r"^\d{3,6}\s+-\s+", part):
            continue

        if "Peruntukan" in part[:300] or "Tanggal Dibentuk" in part[:300]:
            continue

        if "Plafon" not in part and "Baki Debet" not in part:
            continue

        blocks.append(part[:3500])

    return blocks


def extract_kredit_detail(text, posisi_data_date=None):
    kredit_list = []
    blocks = extract_kredit_blocks(text)

    for block in blocks:
        header = block.split("Pelapor Cabang")[0]
        header = header.split("Baki Debet")[0]
        header = re.sub(r"\s+", " ", header).strip()

        kreditur = clean_kreditur(header)

        if not kreditur or len(kreditur) < 4:
            continue

        if kreditur.upper() in ["PT", "BANK", "PERSERO", "TBK"]:
            continue

        money_date = re.search(
            r"Rp\s*([\d\.,]+)\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})",
            block,
            re.IGNORECASE
        )

        baki_debet_txt = money_date.group(1) if money_date else "0"
        tanggal_update = money_date.group(2) if money_date else ""

        jenis_penggunaan = find_first(
            r"Jenis Penggunaan\s+(.+?)\s+Frekuensi Restrukturisasi",
            block
        )

        jenis_kredit = find_first(
            r"Jenis Kredit\/Pembiayaan\s+(.+?)\s+Nilai Proyek",
            block
        )

        plafon_txt = find_first(
            r"\bPlafon\s+Rp\s*([\d\.,]+)",
            block
        )

        plafon_awal_txt = find_first(
            r"Plafon Awal\s+Rp\s*([\d\.,]+)",
            block
        )

        plafon = parse_rupiah(plafon_txt) or parse_rupiah(plafon_awal_txt)
        baki_debet = parse_rupiah(baki_debet_txt)

        kualitas = find_first(
            r"Kualitas\s+(\d)\s*-",
            block,
            default=""
        )

        if not kualitas:
            kualitas = find_first(
                r"No Rekening\s+Kualitas\s+(\d)",
                block,
                default="1"
            )

        kol = safe_int(kualitas, 1)

        tanggal_awal = find_first(
            r"Tanggal Awal Kredit\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})",
            block
        )

        tanggal_mulai = find_first(
            r"Tanggal Mulai\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})",
            block
        )

        tanggal_jt = find_first(
            r"Tanggal Jatuh Tempo\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})",
            block
        )

        tanggal_kondisi = find_first(
            r"Tanggal Kondisi\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4})",
            block
        )

        kondisi = find_first(
            r"Kondisi\s+(.+?)(?:Keterangan|Valuta|Tanggal Kondisi|Akad Kredit|Plafon Awal|$)",
            block
        )

        kondisi_lower = kondisi.lower()

        if "lunas" in kondisi_lower:
            status_label = "LUNAS"
            status = "LUNAS"
        elif "dialihkan" in kondisi_lower or "dijual" in kondisi_lower:
            status_label = "DIALIHKAN"
            status = "DIALIHKAN"
        elif "aktif" in kondisi_lower:
            status_label = "AKTIF"
            status = f"Aktif — JT {tanggal_jt}" if tanggal_jt else "Aktif"
        else:
            status_label = "AKTIF" if baki_debet > 0 else "LUNAS"
            status = (
                f"Aktif — JT {tanggal_jt}"
                if status_label == "AKTIF" and tanggal_jt
                else status_label
            )

        tunggakan_pokok = parse_rupiah(find_first(
            r"Tunggakan Pokok\s+Rp\s*([\d\.,]+)",
            block
        ))

        tunggakan_bunga = parse_rupiah(find_first(
            r"Tunggakan Bunga\s+Rp\s*([\d\.,]+)",
            block
        ))

        denda = parse_rupiah(find_first(
            r"Denda\s+Rp\s*([\d\.,]+)",
            block
        ))

        hari_tunggakan = safe_int(find_first(
            r"Jumlah Hari Tunggakan\s+(\d+)",
            block,
            default="0"
        ))

        jenis_final = jenis_kredit or jenis_penggunaan or "-"
        kategori = kategori_kreditur(kreditur)

        tanggal_awal_final = tanggal_awal or tanggal_mulai
        tanggal_awal_date = parse_tanggal_id(tanggal_awal_final)
        usia_bulan = month_diff(tanggal_awal_date, posisi_data_date)

        is_baru_3_bulan = False
        if usia_bulan is not None and 0 <= usia_bulan <= 3:
            is_baru_3_bulan = True

        is_pinjol = is_pinjol_provider(kreditur, jenis_final)
        is_pinjol_baru_3_bulan = is_pinjol and is_baru_3_bulan

        kredit_list.append({
            "kreditur": kreditur,
            "kategori": kategori,

            "jenis": jenis_final,
            "jenis_penggunaan": jenis_penggunaan or "-",

            "plafon": plafon,
            "plafon_fmt": format_rupiah(plafon),

            "baki_debet": baki_debet,
            "baki_debet_fmt": format_rupiah(baki_debet),

            "kol": kol,
            "kol_saat_ini": kol,

            "status": status,
            "status_label": status_label,

            "tanggal_update": tanggal_update,
            "tanggal_awal": tanggal_awal,
            "tanggal_mulai": tanggal_mulai,
            "tanggal_jatuh_tempo": tanggal_jt,
            "tanggal_kondisi": tanggal_kondisi,

            "tunggakan_pokok": tunggakan_pokok,
            "tunggakan_bunga": tunggakan_bunga,
            "denda": denda,
            "hari_tunggakan": hari_tunggakan,

            "usia_bulan": usia_bulan,
            "is_baru_3_bulan": is_baru_3_bulan,
            "is_pinjol": is_pinjol,
            "is_pinjol_baru_3_bulan": is_pinjol_baru_3_bulan,
        })

    unique = []
    seen = set()

    for k in kredit_list:
        key = (
            k["kreditur"],
            k["plafon"],
            k["baki_debet"],
            k["tanggal_update"],
            k["tanggal_jatuh_tempo"],
            k["status_label"],
        )

        if key not in seen:
            seen.add(key)
            unique.append(k)

    return unique


# =========================
# MAIN EXTRACTOR
# =========================

def extract_basic_fields(text):
    text = normalize_text(text)

    nama = ""

    nama_match = re.search(
        r"([A-Z][A-Z\s]{3,80})\s+NIK\s*/\s*\n?\d{10,20}",
        text,
        re.IGNORECASE
    )

    if nama_match:
        nama = clean_name(nama_match.group(1))

    if not nama:
        nama = clean_name(find_first(
            r"Nama Sesuai Identitas.*?\n([A-Z][A-Z\s]{3,80})",
            text
        ))

    nik = find_first(r"NIK\s*/\s*\n?(\d{10,20})", text)

    if not nik:
        nik_match = re.search(r"\b\d{16}\b", text)
        nik = nik_match.group(0) if nik_match else ""

    nomor_laporan = find_first(
        r"([0-9]+\/IDEB\/[0-9]+\/[0-9]{4})",
        text
    )

    posisi_data = find_first(
        r"Posisi Data Terakhir\s+([A-Za-z]+\s+\d{4})",
        text
    )

    posisi_data_date = parse_tanggal_id(posisi_data)

    tanggal_permintaan = find_first(
        r"Tanggal Permintaan\s+([0-9]{1,2}\s+[A-Za-z]+\s+\d{4}\s+[0-9:]+)",
        text
    )

    ringkasan = find_first(
        r"Ringkasan Fasilitas(.*?)(?:Kredit\/Pembiayaan|Nomor Laporan|$)",
        text
    )

    source_ringkasan = ringkasan if ringkasan else text

    kredit_list = extract_kredit_detail(text, posisi_data_date)

    # =========================
    # KOLEKTIBILITAS TERBURUK
    # Prioritas:
    # 1. Ringkasan resmi SLIK
    # 2. Fallback detail kredit
    # =========================

    kolek = 0
    bulan_kolek = ""

    kolek_match = re.search(
        r"Kolektibilitas\s+Terburuk\s+(\d)\s*/\s*([A-Za-z]+\s+\d{4})",
        source_ringkasan,
        re.IGNORECASE
    )

    if not kolek_match:
        kolek_match = re.search(
            r"(\d)\s*/\s*([A-Za-z]+\s+\d{4})",
            source_ringkasan,
            re.IGNORECASE
        )

    if kolek_match:
        kolek = safe_int(kolek_match.group(1))
        bulan_kolek = kolek_match.group(2).strip()

    kol_list = [
        k["kol"]
        for k in kredit_list
        if k.get("kol")
    ]

    if not kolek and kol_list:
        kolek = max(kol_list)

    # =========================
    # TOTAL PLAFON / BAKI
    # =========================

    plafon_values = re.findall(
        r"Plafon Efektif\s+([\d\.,]+)",
        source_ringkasan,
        re.IGNORECASE
    )

    baki_values = re.findall(
        r"Baki Debet\s+([\d\.,]+)",
        source_ringkasan,
        re.IGNORECASE
    )

    total_plafon = parse_rupiah(plafon_values[-1]) if plafon_values else 0
    total_baki_debet = parse_rupiah(baki_values[-1]) if baki_values else 0

    # =========================
    # KATEGORI KREDITUR
    # dihitung dari kredit_list supaya BPR/BPRS tidak masuk Bank Umum
    # =========================

    bank_umum_set = set()
    bpr_bprs_set = set()
    lembaga_pembiayaan_set = set()
    lainnya_set = set()

    for k in kredit_list:
        kreditur = (k.get("kreditur") or "").strip()

        if not kreditur:
            continue

        kategori = k.get("kategori") or kategori_kreditur(kreditur)

        if kategori == "BPR/BPRS":
            bpr_bprs_set.add(kreditur)
        elif kategori == "BANK UMUM":
            bank_umum_set.add(kreditur)
        elif kategori == "LEMBAGA PEMBIAYAAN":
            lembaga_pembiayaan_set.add(kreditur)
        else:
            lainnya_set.add(kreditur)

    bank_umum = len(bank_umum_set)
    bpr_bprs = len(bpr_bprs_set)
    lembaga_pembiayaan = len(lembaga_pembiayaan_set)
    lainnya = len(lainnya_set)

    jumlah_kreditur = bank_umum + bpr_bprs + lembaga_pembiayaan + lainnya

    # =========================
    # STATUS FASILITAS
    # =========================

    jumlah_aktif = len([
        k for k in kredit_list
        if k["status_label"] == "AKTIF"
    ])

    jumlah_lunas = len([
        k for k in kredit_list
        if k["status_label"] == "LUNAS"
    ])

    total_tunggakan = sum(
        k["tunggakan_pokok"] + k["tunggakan_bunga"]
        for k in kredit_list
    )

    total_baki_debet_aktif = sum(
        k["baki_debet"]
        for k in kredit_list
        if k["status_label"] == "AKTIF"
    )

    if total_baki_debet == 0 and total_baki_debet_aktif > 0:
        total_baki_debet = total_baki_debet_aktif

    if total_plafon == 0:
        total_plafon = sum(k["plafon"] for k in kredit_list)

    jumlah_fasilitas = len(kredit_list)

    fasilitas_baru_3_bulan = [
        k for k in kredit_list
        if k.get("is_baru_3_bulan")
    ]

    pinjol_list = [
        k for k in kredit_list
        if k.get("is_pinjol")
    ]

    pinjol_baru_3_bulan = [
        k for k in kredit_list
        if k.get("is_pinjol_baru_3_bulan")
    ]

    jumlah_fasilitas_baru_3_bulan = len(fasilitas_baru_3_bulan)
    jumlah_pinjol = len(pinjol_list)
    jumlah_pinjol_baru_3_bulan = len(pinjol_baru_3_bulan)

    indikasi_lonjakan_pinjol = jumlah_pinjol_baru_3_bulan >= 2

    if jumlah_pinjol_baru_3_bulan > 0:
        nama_pinjol = [
            f"{k['kreditur']} ({k.get('tanggal_awal') or k.get('tanggal_mulai') or '-'})"
            for k in pinjol_baru_3_bulan[:5]
        ]

        catatan_lonjakan_pinjol = (
            f"Terdapat {jumlah_pinjol_baru_3_bulan} fasilitas dari penyedia digital/fintech "
            f"dalam 3 bulan terakhir: " + "; ".join(nama_pinjol)
        )
    else:
        catatan_lonjakan_pinjol = (
            "Tidak terdeteksi fasilitas pinjol/fintech baru dalam 3 bulan terakhir."
        )

    return {
        "nama": nama,
        "nik": nik,
        "nomor_laporan": nomor_laporan,
        "posisi_data": posisi_data,
        "tanggal_permintaan": tanggal_permintaan,

        "kolektibilitas_list": kol_list,
        "kolektibilitas_terburuk": kolek,
        "bulan_kolektibilitas_terburuk": bulan_kolek,

        "jumlah_indikasi_fasilitas": jumlah_fasilitas,
        "jumlah_kreditur": jumlah_kreditur,
        "bank_umum": bank_umum,
        "bpr_bprs": bpr_bprs,
        "lembaga_pembiayaan": lembaga_pembiayaan,
        "lainnya": lainnya,

        "jumlah_lunas": jumlah_lunas,
        "jumlah_aktif": jumlah_aktif,
        "jumlah_fasilitas_aktif": jumlah_aktif,

        "total_tunggakan": total_tunggakan,
        "total_plafon": total_plafon,
        "total_baki_debet": total_baki_debet,
        "total_baki_debet_aktif": total_baki_debet_aktif,

        "total_plafon_fmt": format_rupiah(total_plafon),
        "total_baki_debet_fmt": format_rupiah(total_baki_debet),
        "total_baki_debet_aktif_fmt": format_rupiah(total_baki_debet_aktif),
        "total_tunggakan_fmt": format_rupiah(total_tunggakan),

        "jumlah_fasilitas_baru_3_bulan": jumlah_fasilitas_baru_3_bulan,
        "jumlah_pinjol": jumlah_pinjol,
        "jumlah_pinjol_baru_3_bulan": jumlah_pinjol_baru_3_bulan,
        "indikasi_lonjakan_pinjol": indikasi_lonjakan_pinjol,
        "catatan_lonjakan_pinjol": catatan_lonjakan_pinjol,

        "pinjol_baru_3_bulan": pinjol_baru_3_bulan,
        "fasilitas_baru_3_bulan": fasilitas_baru_3_bulan,

        "kredit": kredit_list,

        "debug_jumlah_block_kredit": len(extract_kredit_blocks(text)),
        "raw_text_preview": text[:5000],
    }


def parse_slik_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return parse_pdf(filepath)

    if ext in [".xlsx", ".xls"]:
        return parse_excel(filepath)

    raise ValueError("Format file tidak didukung")