# Analisis SLIK OJK

Aplikasi Flask sederhana untuk upload file SLIK PDF/Excel dan menghasilkan analisis awal risiko debitur secara otomatis.

---

## Fitur

* Upload file SLIK PDF / Excel
* Parsing data debitur dan fasilitas kredit
* Analisis risiko otomatis
* Dashboard hasil analisis modern
* Deteksi fasilitas digital / pinjol baru
* Scoring risiko internal
* Export hasil ke PDF
* History hasil analisis
* Multi-user login sederhana
---

# Cara Menjalankan

## 1. Extract folder project

Extract project ke folder yang diinginkan.

Contoh:

```text
D:\PROJECT\analisis-slik
```

---

## 2. Buka terminal / CMD

Masuk ke folder project:

```bash
cd D:\PROJECT\analisis-slik
```

---

## 3. Buat Virtual Environment

```bash
python -m venv venv
```

---

## 4. Aktifkan Virtual Environment

### Windows

```bash
venv\Scripts\activate
```

Jika berhasil biasanya terminal berubah menjadi:

```text
(venv)
```

---

## 5. Install Library

```bash
pip install -r requirements.txt
```

---

# Konfigurasi Environment (.env)

Aplikasi menggunakan file `.env` untuk menyimpan konfigurasi login, secret key, dan konfigurasi AI.

Buat file `.env` di folder utama project.

Contoh isi `.env`:

```env
SECRET_KEY=ganti_dengan_secret_key_sendiri

APP_USERS=admin:admin123,user:user123
```
---

## Format APP_USERS

Format:

```text
username:password
```

Jika lebih dari satu user:

```text
admin:admin123,user:user123,manager:manager123
```

---

## Contoh Login

```text
Username: admin
Password: admin123
```

atau:

```text
Username: user
Password: user123
```

---

# Menjalankan Aplikasi

```bash
python app.py
```

---

# Membuka Aplikasi

Buka browser:

```text
http://localhost:5000
```

---

# Akses dari Jaringan Internal Kantor

Cari IP komputer server:

```bash
ipconfig
```

Contoh:

```text
IPv4 Address : 192.168.1.10
```

Komputer lain dalam jaringan bisa mengakses:

```text
http://192.168.1.10:5000
```

Pastikan firewall Windows mengizinkan port 5000.

---
# Catatan Penting

* Ini adalah versi awal / prototype internal.
* Parser mungkin perlu disesuaikan dengan format SLIK tertentu.
* Hasil sistem bukan keputusan final kredit.
* Hasil wajib diverifikasi analis kredit.
* Untuk keamanan data SLIK, aplikasi sebaiknya tetap digunakan di jaringan internal kantor.
---

# Teknologi yang Digunakan

* Python
* Flask
* Bootstrap 5
* Chart.js
* SQLite
---
