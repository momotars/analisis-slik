# AI Analisis SLIK OJK - Versi Awal Localhost

Aplikasi Flask sederhana untuk upload file SLIK PDF/Excel dan menghasilkan analisis awal risiko debitur.

## Cara Menjalankan

1. Extract folder project.
2. Buka terminal/CMD di folder project.
3. Buat virtual environment:

```bash
python -m venv venv
```

4. Aktifkan virtual environment:

Windows:
```bash
venv\Scripts\activate
```

5. Install library:

```bash
pip install -r requirements.txt
```

6. Jalankan aplikasi:

```bash
python app.py
```

7. Buka browser:

```text
http://localhost:5000
```

## Akses dari jaringan internal kantor

Cari IP komputer yang menjalankan aplikasi:

```bash
ipconfig
```

Misal IP komputer server adalah `192.168.1.10`, maka komputer lain bisa akses:

```text
http://192.168.1.10:5000
```

Pastikan firewall Windows mengizinkan port 5000.

## Catatan Penting

- Ini adalah versi awal/prototype.
- Parser perlu disesuaikan dengan format file SLIK asli.
- Jangan jadikan hasil AI sebagai keputusan final.
- Hasil wajib diverifikasi analis kredit.
- Untuk data SLIK, sebaiknya aplikasi tetap di jaringan internal.
