def format_rupiah(value):
    try:
        return "Rp {:,}".format(int(value or 0)).replace(",", ".")
    except Exception:
        return "Rp 0"


def safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def analyze_slik(data):
    score = 0

    score_details = []
    critical_risks = []
    warnings = []
    positives = []
    clarifications = []

    kolek = safe_int(data.get("kolektibilitas_terburuk", 0))
    bulan_kolek = data.get("bulan_kolektibilitas_terburuk", "")

    tunggakan = safe_int(data.get("total_tunggakan", 0))
    jumlah_fasilitas = safe_int(data.get("jumlah_indikasi_fasilitas", 0))
    jumlah_fasilitas_aktif = safe_int(
        data.get("jumlah_fasilitas_aktif", data.get("jumlah_aktif", 0))
    )
    jumlah_kreditur = safe_int(data.get("jumlah_kreditur", 0))
    baki_debet = safe_int(data.get("total_baki_debet", 0))

    jumlah_fasilitas_baru_3_bulan = safe_int(
        data.get("jumlah_fasilitas_baru_3_bulan", 0)
    )
    jumlah_pinjol = safe_int(data.get("jumlah_pinjol", 0))
    jumlah_pinjol_baru_3_bulan = safe_int(
        data.get("jumlah_pinjol_baru_3_bulan", 0)
    )
    indikasi_lonjakan_pinjol = data.get("indikasi_lonjakan_pinjol", False)
    catatan_lonjakan_pinjol = data.get("catatan_lonjakan_pinjol", "")

    kredit_list = data.get("kredit", []) or []

    aktif_list = []
    lunas_list = []

    kol1_aktif = 0
    kol2_aktif = 0
    kol3plus_aktif = 0
    kol5_aktif = 0

    kol5_lunas = 0
    plafon_penuh_list = []

    for k in kredit_list:
        kol = safe_int(k.get("kol", 0))
        status_label = str(k.get("status_label", "") or "").upper()
        status = str(k.get("status", "") or "").upper()

        plafon = safe_int(k.get("plafon", 0))
        baki = safe_int(k.get("baki_debet", 0))

        is_lunas = status_label == "LUNAS" or "LUNAS" in status
        is_aktif = status_label == "AKTIF" or (not is_lunas and baki > 0)

        if is_lunas:
            lunas_list.append(k)

            if kol >= 5:
                kol5_lunas += 1

        elif is_aktif:
            aktif_list.append(k)

            if kol == 1:
                kol1_aktif += 1
            elif kol == 2:
                kol2_aktif += 1
            elif kol >= 3:
                kol3plus_aktif += 1

            if kol >= 5:
                kol5_aktif += 1

            if plafon > 0 and baki >= plafon:
                plafon_penuh_list.append(k)

    if jumlah_fasilitas_aktif <= 0:
        jumlah_fasilitas_aktif = len(aktif_list)

    jumlah_lunas = len(lunas_list)

    # =========================
    # KOLEKTIBILITAS TERBURUK
    # Catatan:
    # - Kolektibilitas terburuk dari ringkasan SLIK bersifat historis.
    # - Jika Kol 5 sudah lunas, tidak disamakan dengan Kol 5 aktif.
    # =========================

    if kolek >= 5:
        if kol5_aktif > 0:
            score += 100
            critical_risks.append(
                "Terdapat fasilitas aktif dengan riwayat kolektibilitas 5 / macet."
            )
            clarifications.append(
                "Perlu klarifikasi status penyelesaian fasilitas aktif dengan riwayat Kol 5."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 5 aktif",
                "dampak": "+100"
            })

        elif kol5_lunas > 0:
            score += 40
            warnings.append(
                f"Terdapat riwayat kolektibilitas 5 pada fasilitas yang telah lunas"
                f"{' (' + bulan_kolek + ')' if bulan_kolek else ''}."
            )
            positives.append(
                "Riwayat Kol 5 terindikasi sudah tidak memiliki baki debet aktif pada fasilitas tersebut."
            )
            clarifications.append(
                "Perlu klarifikasi penyebab riwayat Kol 5 dan bukti penyelesaian/lunas."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 5 historis/lunas",
                "dampak": "+40"
            })

        else:
            score += 50
            warnings.append(
                f"Terdapat riwayat kolektibilitas 5 secara historis"
                f"{' (' + bulan_kolek + ')' if bulan_kolek else ''}."
            )
            clarifications.append(
                "Perlu klarifikasi fasilitas penyebab Kol 5 historis."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 5 historis",
                "dampak": "+50"
            })

    elif kolek == 4:
        if kol3plus_aktif > 0:
            score += 70
            critical_risks.append(
                "Terdapat riwayat kolektibilitas 4 / diragukan."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 4",
                "dampak": "+70"
            })
        else:
            score += 45
            warnings.append(
                "Terdapat riwayat kolektibilitas 4 secara historis."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 4 historis",
                "dampak": "+45"
            })

    elif kolek == 3:
        if kol3plus_aktif > 0:
            score += 40
            warnings.append(
                "Terdapat fasilitas aktif dengan kolektibilitas Kol 3 atau lebih."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 3 aktif",
                "dampak": "+40"
            })
        else:
            score += 25
            warnings.append(
                "Terdapat riwayat kolektibilitas 3 secara historis."
            )
            score_details.append({
                "faktor": "Kolektibilitas",
                "kondisi": "Kol 3 historis",
                "dampak": "+25"
            })

    elif kolek == 2:
        score += 20
        warnings.append(
            f"Kolektibilitas terburuk berada pada Kol 2 / Dalam Perhatian Khusus"
            f"{' (' + bulan_kolek + ')' if bulan_kolek else ''}."
        )
        score_details.append({
            "faktor": "Kolektibilitas",
            "kondisi": "Kol 2",
            "dampak": "+20"
        })

    elif kolek == 1:
        positives.append("Kolektibilitas terburuk terdeteksi Kol 1 / lancar.")
        score_details.append({
            "faktor": "Kolektibilitas",
            "kondisi": "Kol 1",
            "dampak": "+0"
        })

    else:
        warnings.append("Data kolektibilitas belum terdeteksi oleh parser.")

    # =========================
    # TUNGGAKAN
    # =========================

    if tunggakan > 0:
        score += 15
        critical_risks.append(
            f"Terdapat tunggakan sebesar {format_rupiah(tunggakan)}."
        )
        clarifications.append(
            "Perlu klarifikasi penyebab tunggakan dan status penyelesaiannya."
        )
        score_details.append({
            "faktor": "Tunggakan",
            "kondisi": format_rupiah(tunggakan),
            "dampak": "+15"
        })
    else:
        positives.append("Tidak terdeteksi tunggakan pada data SLIK.")

    # =========================
    # POLA KOLEKTIBILITAS AKTIF
    # =========================

    if jumlah_fasilitas_aktif > 0 and kol2_aktif > 0:
        if kol2_aktif >= 5 or kol2_aktif >= (jumlah_fasilitas_aktif * 0.5):
            score += 20
            warnings.append(
                f"{kol2_aktif} dari {jumlah_fasilitas_aktif} fasilitas aktif berstatus Kol 2 secara bersamaan."
            )
            clarifications.append(
                "Apa penyebab beberapa fasilitas aktif berada pada Kol 2 secara bersamaan?"
            )
            score_details.append({
                "faktor": "Pola Kol 2 Aktif",
                "kondisi": f"{kol2_aktif} dari {jumlah_fasilitas_aktif} fasilitas aktif",
                "dampak": "+20"
            })

    if kol3plus_aktif > 0:
        score += 25
        critical_risks.append(
            f"Terdapat {kol3plus_aktif} fasilitas aktif dengan kolektibilitas Kol 3 atau lebih."
        )
        clarifications.append(
            "Perlu klarifikasi fasilitas aktif dengan Kol 3 atau lebih."
        )
        score_details.append({
            "faktor": "Kol 3+ Aktif",
            "kondisi": f"{kol3plus_aktif} fasilitas",
            "dampak": "+25"
        })

    if jumlah_fasilitas_aktif > 0 and kol1_aktif == jumlah_fasilitas_aktif:
        positives.append("Seluruh fasilitas aktif terdeteksi Kol 1 / lancar.")

    # =========================
    # JUMLAH FASILITAS / KREDITUR
    # =========================

    if jumlah_fasilitas >= 20:
        score += 20
        warnings.append(
            f"Jumlah fasilitas kredit sangat banyak yaitu {jumlah_fasilitas} fasilitas."
        )
        score_details.append({
            "faktor": "Jumlah Fasilitas",
            "kondisi": f"{jumlah_fasilitas} fasilitas",
            "dampak": "+20"
        })

    elif jumlah_fasilitas >= 10:
        score += 10
        warnings.append(
            f"Jumlah fasilitas kredit cukup banyak yaitu {jumlah_fasilitas} fasilitas."
        )
        score_details.append({
            "faktor": "Jumlah Fasilitas",
            "kondisi": f"{jumlah_fasilitas} fasilitas",
            "dampak": "+10"
        })
    else:
        positives.append("Jumlah fasilitas kredit masih dalam batas wajar.")

    if jumlah_kreditur >= 10:
        score += 10
        warnings.append(
            f"Terdapat {jumlah_kreditur} kreditur/lembaga pembiayaan."
        )
        clarifications.append(
            "Perlu klarifikasi total kewajiban aktif pada seluruh kreditur."
        )
        score_details.append({
            "faktor": "Jumlah Kreditur",
            "kondisi": f"{jumlah_kreditur} kreditur",
            "dampak": "+10"
        })

    # =========================
    # BAKI DEBET
    # =========================

    if baki_debet >= 300_000_000:
        score += 20
        warnings.append(
            f"Total baki debet besar yaitu {format_rupiah(baki_debet)}."
        )
        score_details.append({
            "faktor": "Baki Debet",
            "kondisi": format_rupiah(baki_debet),
            "dampak": "+20"
        })

    elif baki_debet >= 100_000_000:
        score += 10
        warnings.append(
            f"Total baki debet cukup besar yaitu {format_rupiah(baki_debet)}."
        )
        score_details.append({
            "faktor": "Baki Debet",
            "kondisi": format_rupiah(baki_debet),
            "dampak": "+10"
        })
    else:
        positives.append("Total baki debet tidak terlalu besar.")

    # =========================
    # BAKI DEBET = PLAFON
    # =========================

    if plafon_penuh_list:
        score += 15

        for k in plafon_penuh_list[:3]:
            kreditur = k.get("kreditur", "-")
            baki = safe_int(k.get("baki_debet", 0))
            warnings.append(
                f"{kreditur} memiliki baki debet sama atau lebih besar dari plafon ({format_rupiah(baki)})."
            )

        clarifications.append(
            "Perlu klarifikasi fasilitas dengan baki debet sama dengan plafon."
        )
        score_details.append({
            "faktor": "Baki Debet = Plafon",
            "kondisi": f"{len(plafon_penuh_list)} fasilitas",
            "dampak": "+15"
        })

    # =========================
    # FASILITAS BARU
    # =========================

    if jumlah_fasilitas_baru_3_bulan >= 5:
        score += 20
        warnings.append(
            f"Terdapat {jumlah_fasilitas_baru_3_bulan} fasilitas baru dalam 3 bulan terakhir."
        )
        clarifications.append(
            "Perlu klarifikasi tujuan pembukaan beberapa fasilitas baru."
        )
        score_details.append({
            "faktor": "Fasilitas Baru",
            "kondisi": f"{jumlah_fasilitas_baru_3_bulan} fasilitas baru",
            "dampak": "+20"
        })

    elif jumlah_fasilitas_baru_3_bulan >= 2:
        score += 10
        warnings.append(
            f"Terdapat {jumlah_fasilitas_baru_3_bulan} fasilitas baru dalam 3 bulan terakhir."
        )
        score_details.append({
            "faktor": "Fasilitas Baru",
            "kondisi": f"{jumlah_fasilitas_baru_3_bulan} fasilitas baru",
            "dampak": "+10"
        })
    else:
        positives.append(
            "Tidak terdeteksi pembukaan fasilitas baru yang signifikan dalam 3 bulan terakhir."
        )

    # =========================
    # PINJOL / FINTECH
    # =========================

    if jumlah_pinjol > 10:
        score += 20
        warnings.append(
            f"Terdapat {jumlah_pinjol} fasilitas dari penyedia digital/fintech/pinjol."
        )
        clarifications.append(
            "Perlu klarifikasi penggunaan fasilitas digital/fintech/pinjol."
        )
        score_details.append({
            "faktor": "Fintech / Pinjol",
            "kondisi": f"{jumlah_pinjol} fasilitas",
            "dampak": "+20"
        })

    elif jumlah_pinjol > 5:
        score += 10
        warnings.append(
            f"Terdapat {jumlah_pinjol} fasilitas dari penyedia digital/fintech/pinjol."
        )
        score_details.append({
            "faktor": "Fintech / Pinjol",
            "kondisi": f"{jumlah_pinjol} fasilitas",
            "dampak": "+10"
        })

    elif jumlah_pinjol > 0:
        warnings.append(
            f"Terdapat {jumlah_pinjol} fasilitas dari penyedia digital/fintech/pinjol."
        )

    else:
        positives.append("Tidak terdeteksi fasilitas digital/fintech/pinjol.")

    if indikasi_lonjakan_pinjol:
        score += 15
        warnings.append(
            f"Terdapat lonjakan pinjol/fintech dalam 3 bulan terakhir "
            f"({jumlah_pinjol_baru_3_bulan} fasilitas baru)."
        )
        clarifications.append(
            "Perlu klarifikasi lonjakan fasilitas digital/fintech dalam 3 bulan terakhir."
        )
        score_details.append({
            "faktor": "Lonjakan Pinjol",
            "kondisi": f"{jumlah_pinjol_baru_3_bulan} fasilitas baru",
            "dampak": "+15"
        })

    if catatan_lonjakan_pinjol:
        warnings.append(catatan_lonjakan_pinjol)

    # =========================
    # POSITIF TAMBAHAN
    # =========================

    if jumlah_lunas > 0:
        positives.append(
            f"Terdapat {jumlah_lunas} fasilitas historis yang telah lunas."
        )

    if kolek >= 5 and kol5_aktif == 0:
        positives.append(
            "Tidak terdeteksi fasilitas aktif dengan status Kol 5."
        )

    if jumlah_fasilitas_aktif == 0:
        positives.append(
            "Tidak terdeteksi fasilitas aktif dengan baki debet berjalan."
        )

    # =========================
    # RULE CAPPING UNTUK DEBITUR LANCAR (KOL 1 & TANPA TUNGGAKAN)
    # =========================
    is_lancar_bersih = (kolek <= 1) and (tunggakan == 0) and (kol3plus_aktif == 0) and (kol2_aktif == 0)

    if is_lancar_bersih:
        # Debitur 100% lancar dan tanpa tunggakan dibatasi skor maksimalnya di 34 (Kategori RENDAH)
        # Hal ini memberikan pembeda (score lebih besar dari 0 jika debitur memiliki banyak fasilitas/paylater),
        # namun menjamin debitur tidak jatuh ke kategori risiko SEDANG/TINGGI yang dapat mempersulit persetujuan.
        if score > 34:
            score_details.append({
                "faktor": "Capping Debitur Lancar",
                "kondisi": "Kol 1 & Tanpa Tunggakan",
                "dampak": f"Skor disesuaikan dari {score} menjadi 34"
            })
            score = 34

    # =========================
    # SCORE FINAL
    # =========================

    score = min(score, 100)

    if score >= 70:
        risk = "TINGGI"
        decision_label = "PERHATIAN KHUSUS"
    elif score >= 35:
        risk = "SEDANG"
        decision_label = "PERLU KLARIFIKASI"
    else:
        risk = "RENDAH"
        decision_label = "DAPAT DILANJUTKAN DENGAN VERIFIKASI"


    # =========================
    # RINGKASAN FAKTUAL
    # =========================

    summary_parts = []

    if jumlah_fasilitas_aktif:
        summary_parts.append(f"{jumlah_fasilitas_aktif} fasilitas aktif")

    if jumlah_kreditur:
        summary_parts.append(f"{jumlah_kreditur} kreditur")

    if baki_debet:
        summary_parts.append(f"baki debet {format_rupiah(baki_debet)}")

    if kolek:
        if bulan_kolek:
            summary_parts.append(f"kol terburuk historis {kolek} ({bulan_kolek})")
        else:
            summary_parts.append(f"kol terburuk historis {kolek}")

    if summary_parts:
        risk_summary = (
            f"Debitur terdeteksi memiliki {', '.join(summary_parts)}. "
            f"Kategori risiko: {risk} dengan score {score}/100."
        )
    else:
        risk_summary = (
            f"Kategori risiko: {risk} dengan score {score}/100."
        )

    if not clarifications:
        clarifications.append(
            "Verifikasi penghasilan, tujuan pinjaman, dan kemampuan bayar tetap diperlukan."
        )

    recommendation = decision_label

    # compatibility field lama
    findings = []
    findings.extend(critical_risks)
    findings.extend(warnings)
    findings.extend(positives)

    main_reasons = []
    main_reasons.extend(critical_risks)
    main_reasons.extend(warnings)

    return {
        "score": score,
        "risk": risk,
        "risk_summary": risk_summary,
        "decision_label": decision_label,

        "critical_risks": critical_risks,
        "warnings": warnings,
        "positives": positives,
        "clarifications": clarifications,

        "recommendation": recommendation,
        "score_details": score_details,

        "findings": findings,
        "main_reasons": main_reasons,
        "positive_points": positives,
    }