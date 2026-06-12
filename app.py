from flask import Flask, render_template, request, redirect, flash, session, send_file, abort
import os
import tempfile
import json
from functools import wraps
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import check_password_hash

from parser_slik import parse_slik_file
from analyzer import analyze_slik
from ai_helper import generate_ai_analysis
from database import init_db, save_history, get_history, get_history_by_id


from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# =========================
# LOAD ENV
# =========================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "xlsx", "xls"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

init_db()



# =========================
# USER MANAGEMENT
# Format .env:
# APP_USERS=admin:admin123:admin,staff:staff123:user
# =========================
def load_users():
    users_raw = os.getenv("APP_USERS", "")
    users = {}

    for item in users_raw.split(","):
        item = item.strip()
        if not item:
            continue

        parts = item.split(":")
        if len(parts) != 3:
            continue

        username, password, role = parts
        users[username] = {
            "password": password,
            "role": role
        }

    return users


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")

        if session.get("role") != "admin":
            abort(403)

        return f(*args, **kwargs)
    return wrapper


# =========================
# AUTH
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()
        user = users.get(username)

        if user:
            # Dukung password terenkripsi (check_password_hash) atau plaintext
            is_valid = (password == user["password"]) or check_password_hash(user["password"], password)
            if is_valid:
                session["logged_in"] = True
                session["username"] = username
                session["role"] = user["role"]
                return redirect("/")

        flash("Username atau password salah.")
        return redirect("/login")

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# MAIN PAGE
# =========================
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":

        if "file" not in request.files:
            flash("File belum dipilih.")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("File belum dipilih.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            try:
                extracted = parse_slik_file(filepath)
                result = analyze_slik(extracted)
                ai_text = generate_ai_analysis(extracted)

                history_id = save_history(
                    username=session.get("username", "unknown"),
                    filename=filename,
                    extracted=extracted,
                    result=result,
                    ai_text=ai_text
                )

                session["last_history_id"] = history_id

                return render_template(
                    "result.html",
                    extracted=extracted,
                    result=result,
                    ai_text=ai_text,
                    filename=filename,
                    history_id=history_id,
                    role=session.get("role")
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Gagal memproses berkas SLIK: {str(e)}")
                return redirect("/")

        flash("Format file tidak didukung.")
        return redirect(request.url)

    return render_template(
        "index.html",
        role=session.get("role")
    )



# =========================
# EXPORT PDF
# =========================
@app.route("/export-pdf")
@app.route("/export-pdf/<int:history_id>")
@login_required
def export_pdf(history_id=None):
    if history_id is None:
        history_id = session.get("last_history_id")

    if not history_id:
        flash("Silakan upload dan analisis SLIK terlebih dahulu sebelum export PDF.")
        return redirect("/")

    row = get_history_by_id(history_id)
    if not row:
        flash("Riwayat analisis tidak ditemukan.")
        return redirect("/")

    # Menguraikan data JSON dari DB atau memuat fallback jika kolom kosong (data lama)
    try:
        extracted = json.loads(row["extracted_json"]) if row["extracted_json"] else {}
        result = json.loads(row["result_json"]) if row["result_json"] else {}
    except Exception:
        extracted = {}
        result = {}

    # Mengisi data fallback dari data kolom sql jika JSON tidak valid/kosong
    if not extracted:
        extracted = {
            "nama": row["nama"],
            "nik": row["nik"],
            "nomor_laporan": row["filename"],
            "posisi_data": row["bulan_kolektibilitas"],
            "tanggal_permintaan": row["created_at"],
            "kolektibilitas_terburuk": row["kolektibilitas"],
            "bulan_kolektibilitas_terburuk": row["bulan_kolektibilitas"],
            "total_plafon": row["total_plafon"],
            "total_baki_debet": row["total_baki_debet"],
            "total_tunggakan": row["total_tunggakan"],
            "jumlah_kreditur": row["jumlah_kreditur"],
        }
    if not result:
        result = {
            "risk": row["risiko"],
            "recommendation": row["rekomendasi"],
            "findings": []
        }

    ai_text = row["ai_text"]

    pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    doc = SimpleDocTemplate(
        pdf_file.name,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0d47a1"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=16
    )

    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0d47a1"),
        spaceBefore=10,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontSize=9,
        leading=13
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.grey
    )

    ai_style = ParagraphStyle(
        "AIStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        leftIndent=6,
        rightIndent=6
    )

    elements = []

    def rupiah(value):
        try:
            return "Rp {:,}".format(int(value)).replace(",", ".")
        except Exception:
            return "Rp 0"

    def safe_text(value):
        if value is None:
            return "-"
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def make_info_table(rows):
        table_data = []
        for label, value in rows:
            table_data.append([
                Paragraph(f"<b>{safe_text(label)}</b>", normal_style),
                Paragraph(safe_text(value), normal_style)
            ])

        table = Table(table_data, colWidths=[145, 360])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7de")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    def make_kreditur_table():
        table = Table([
            [
                Paragraph("<b>Bank Umum</b>", normal_style),
                Paragraph("<b>BPR/BPRS</b>", normal_style),
                Paragraph("<b>Lembaga Pembiayaan</b>", normal_style),
                Paragraph("<b>Lainnya</b>", normal_style),
            ],
            [
                Paragraph(str(extracted.get("bank_umum", 0)), normal_style),
                Paragraph(str(extracted.get("bpr_bprs", 0)), normal_style),
                Paragraph(str(extracted.get("lembaga_pembiayaan", 0)), normal_style),
                Paragraph(str(extracted.get("lainnya", 0)), normal_style),
            ]
        ], colWidths=[120, 120, 145, 120])

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7de")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3f2fd")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return table

    risk = result.get("risk", "-")
    if risk == "TINGGI":
        risk_color = colors.HexColor("#dc3545")
    elif risk == "SEDANG":
        risk_color = colors.HexColor("#f59f00")
    else:
        risk_color = colors.HexColor("#198754")

    elements.append(Paragraph("LAPORAN ANALISIS SLIK", title_style))
    elements.append(Paragraph("Dokumen bantu analisis awal kredit", subtitle_style))

    elements.append(Paragraph("Data Debitur", section_style))
    elements.append(make_info_table([
        ["Nama", extracted.get("nama", "-")],
        ["NIK", extracted.get("nik", "-")],
        ["Nomor Laporan", extracted.get("nomor_laporan", "-")],
        ["Posisi Data", extracted.get("posisi_data", "-")],
        ["Tanggal Permintaan", extracted.get("tanggal_permintaan", "-")],
    ]))

    elements.append(Paragraph("Ringkasan Fasilitas", section_style))
    elements.append(make_info_table([
        ["Kolektibilitas", f"{extracted.get('kolektibilitas_terburuk', '-')} / {extracted.get('bulan_kolektibilitas_terburuk', '-')}"],
        ["Total Plafon", rupiah(extracted.get("total_plafon", 0))],
        ["Baki Debet", rupiah(extracted.get("total_baki_debet", 0))],
        ["Total Tunggakan", rupiah(extracted.get("total_tunggakan", 0))],
        ["Jumlah Kreditur", str(extracted.get("jumlah_kreditur", 0))],
    ]))

    elements.append(Paragraph("Komposisi Kreditur", section_style))
    elements.append(make_kreditur_table())

    elements.append(Paragraph("Analisis Sistem", section_style))
    risk_table = Table([
        [
            Paragraph("<b>Risiko</b>", normal_style),
            Paragraph(f"<b>{safe_text(risk)}</b>", ParagraphStyle(
                "RiskStyle",
                parent=normal_style,
                textColor=risk_color
            ))
        ]
    ], colWidths=[145, 360])
    risk_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d7de")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 6))

    for item in result.get("findings", []):
        elements.append(Paragraph(f"• {safe_text(item)}", normal_style))

    elements.append(Spacer(1, 5))
    elements.append(Paragraph(f"<b>Rekomendasi:</b> {safe_text(result.get('recommendation', '-'))}", normal_style))

    # Tampilkan Analisis Narasi AI ke PDF
    if ai_text:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Analisis Narasi AI", section_style))
        for line in ai_text.splitlines():
            line = line.strip()
            if not line:
                continue
            # Jika baris berupa judul sub-bagian AI
            if line in ["RINGKASAN PROFIL", "ANALISIS RISIKO", "CATATAN PENTING", "REKOMENDASI / KLARIFIKASI"]:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph(f"<b>{safe_text(line)}</b>", ParagraphStyle(
                    "AIHeading",
                    parent=normal_style,
                    textColor=colors.HexColor("#0d47a1"),
                    spaceBefore=4,
                    spaceAfter=2,
                    keepWithNext=True
                )))
            else:
                # Menampilkan poin bullet dari teks AI
                elements.append(Paragraph(safe_text(line), ai_style))

    elements.append(Spacer(1, 14))
    elements.append(Paragraph(
        "Catatan: Laporan ini merupakan alat bantu analisis awal. Keputusan kredit tetap wajib diverifikasi oleh analis/pejabat berwenang.",
        small_style
    ))

    doc.build(elements)

    client_name = secure_filename(extracted.get("nama", "debitur")).replace(" ", "_")
    download_filename = f"laporan_analisis_slik_{client_name}.pdf"

    return send_file(
        pdf_file.name,
        as_attachment=True,
        download_name=download_filename
    )


# =========================
# HISTORY - ADMIN ONLY
# =========================
@app.route("/history")
@admin_required
def history():
    data = get_history()
    return render_template("history.html", data=data)


# =========================
# ERROR PAGE
# =========================
@app.errorhandler(403)
def forbidden(e):
    return """
    <h3>Akses ditolak</h3>
    <p>Halaman ini hanya bisa diakses oleh admin.</p>
    <a href="/">Kembali</a>
    """, 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)