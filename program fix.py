import csv
import math
import os
import re
import sys

try:
    FOLDER_PROGRAM = os.path.dirname(os.path.abspath(__file__))
except NameError:
    FOLDER_PROGRAM = os.getcwd()

FILE_DEFAULT = "student_spending.csv"
KOLOM_PEMASUKAN = "monthly_income"

KODE_KATEGORI = [
    "housing", "food", "transportation", "books_supplies", "entertainment",
    "personal_care", "technology", "health_wellness", "miscellaneous",
]
KOLOM_WAJIB = [KOLOM_PEMASUKAN] + KODE_KATEGORI

NAMA_KATEGORI = {
    "housing": "Tempat tinggal",
    "food": "Makanan",
    "transportation": "Transportasi",
    "books_supplies": "Kebutuhan kuliah",
    "entertainment": "Hiburan",
    "personal_care": "Kebutuhan pribadi",
    "technology": "Teknologi",
    "health_wellness": "Kesehatan",
    "miscellaneous": "Lainnya",
}

JENIS_KATEGORI = {
    "housing": "Kebutuhan",
    "food": "Kebutuhan",
    "transportation": "Kebutuhan",
    "books_supplies": "Kebutuhan",
    "personal_care": "Kebutuhan",
    "health_wellness": "Kebutuhan",
    "entertainment": "Keinginan",
    "technology": "Keinginan",
    "miscellaneous": "Keinginan",
}
DAFTAR_JENIS = ("Kebutuhan", "Keinginan")

ANGGARAN_DEFAULT_PERSEN = {
    "housing": 30, "food": 10, "transportation": 5, "books_supplies": 5,
    "personal_care": 2, "health_wellness": 3,
    "entertainment": 10, "technology": 8, "miscellaneous": 7,
}

KOLOM_ID = ("student_id", "id", "")
ALIAS_KOLOM_TAMBAHAN = {
    "jurusan": ("major", "jurusan", "program_studi", "prodi", "department", "study_program"),
    "umur": ("age", "umur", "usia"),
    "gender": ("gender", "jenis_kelamin"),
}

BATAS_ATAS_NILAI = 1_000_000_000_000
BARIS_PER_HALAMAN = 10


class KesalahanData(Exception):
    pass


def format_angka(nilai):
    return f"{nilai:,.2f}"


def format_persen(nilai):
    return "-" if nilai is None else f"{nilai:.1f}%"


def hitung_persen(bagian, total):
    return 0.0 if total == 0 else bagian / total * 100


def ke_bilangan_bulat(teks):
    try:
        return int(str(teks).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def ke_angka(teks):
    if teks is None:
        return None
    teks_bersih = re.sub(r"(?i)\brp\b", "", str(teks)).strip()
    if teks_bersih == "":
        return None
    if re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+(,\d+)?", teks_bersih):
        teks_bersih = teks_bersih.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+(\.\d+)?", teks_bersih):
        teks_bersih = teks_bersih.replace(",", "")
    else:
        teks_bersih = teks_bersih.replace(",", ".")
    try:
        angka = float(teks_bersih)
    except ValueError:
        return None
    return angka if math.isfinite(angka) else None


def status_kas(sisa):
    if sisa > 0:
        return "Surplus (Aman)"
    if sisa < 0:
        return "Defisit (Boros)"
    return "Impas"


def status_anggaran(selisih):
    if selisih > 0:
        return "SISA"
    if selisih < 0:
        return "MELEBIHI"
    return "TEPAT"


def hitung_anggaran(pemasukan, persen):
    return round(pemasukan * persen / 100, 2)


def hitung_pemakaian(realisasi, anggaran):
    return None if anggaran == 0 else realisasi / anggaran * 100


def gabung_nama(kode_kategori):
    return " dan ".join(NAMA_KATEGORI[k] for k in kode_kategori)


def jeda_layar():
    input("\nTekan [Enter] untuk kembali ke menu utama...")


def garis(karakter="-", lebar=106):
    print(karakter * lebar)


def judul(teks):
    print()
    garis("=")
    print("  " + teks)
    garis("=")


def cari_file(path):
    nama = str(path).strip().strip('"').strip("'")
    if nama == "":
        raise KesalahanData("Nama file data belum diisi.")
    for lokasi in (nama, os.path.join(FOLDER_PROGRAM, nama)):
        if os.path.isfile(lokasi):
            return lokasi
    raise KesalahanData(f"File '{nama}' tidak ditemukan di folder kerja maupun di '{FOLDER_PROGRAM}'.")


def baca_baris_mentah(path):
    lokasi = cari_file(path)
    hasil = []
    try:
        with open(lokasi, newline="", encoding="utf-8-sig") as berkas:
            pembaca = csv.reader(berkas)
            baris_header = next(pembaca, None)
            if baris_header is None or not any(sel.strip() for sel in baris_header):
                raise KesalahanData("File data kosong dan tidak memiliki header.")
            header = [sel.strip().lower() for sel in baris_header]
            hilang = [kolom for kolom in KOLOM_WAJIB if kolom not in header]
            if hilang:
                raise KesalahanData(
                    "Kolom wajib tidak ditemukan: " + ", ".join(hilang)
                    + " | Kolom yang terbaca: " + ", ".join(header)
                )
            for isi in pembaca:
                if not isi or not any(sel.strip() for sel in isi):
                    continue
                baris = {nama_kolom: (isi[i] if i < len(isi) else None) for i, nama_kolom in enumerate(header)}
                hasil.append((pembaca.line_num, baris))
    except PermissionError:
        raise KesalahanData(f"Tidak memiliki izin membaca file '{path}'.")
    except UnicodeDecodeError:
        raise KesalahanData("File gagal didekode sebagai UTF-8. Simpan ulang CSV dalam encoding UTF-8.")
    except csv.Error as galat:
        raise KesalahanData("Format CSV tidak valid: " + str(galat))
    except OSError as galat:
        raise KesalahanData("File gagal dibuka: " + str(galat))
    if not hasil:
        raise KesalahanData("File hanya berisi header tanpa baris data.")
    return hasil


def validasi_baris(baris):
    nilai = {}
    masalah = []
    for kolom in KOLOM_WAJIB:
        teks = baris.get(kolom)
        if teks is None or teks.strip() == "":
            masalah.append(kolom + ": kosong")
            continue
        angka = ke_angka(teks)
        if angka is None:
            masalah.append(kolom + ": bukan angka ('" + teks.strip() + "')")
        elif angka < 0:
            masalah.append(kolom + ": negatif (" + teks.strip() + ")")
        elif angka > BATAS_ATAS_NILAI:
            masalah.append(kolom + ": melebihi batas wajar (" + teks.strip() + ")")
        else:
            nilai[kolom] = angka
    if nilai.get(KOLOM_PEMASUKAN) == 0:
        masalah.append(KOLOM_PEMASUKAN + ": harus lebih dari 0")
    return (None, masalah) if masalah else (nilai, [])


def ambil_id(baris, urutan):
    for kolom in KOLOM_ID:
        teks = baris.get(kolom)
        if teks is not None and teks.strip() != "":
            return teks.strip()
    return str(urutan)


def ambil_teks_opsional(baris, daftar_alias):
    for kolom in daftar_alias:
        teks = baris.get(kolom)
        if teks is not None and teks.strip() != "":
            return " ".join(teks.strip().split())
    return None


def kelompokkan_umur(teks_umur):
    angka = ke_angka(teks_umur)
    if angka is None or angka < 0:
        return None
    usia = int(angka) if angka.is_integer() else angka
    if usia <= 18:
        return "<= 18 tahun"
    if usia <= 20:
        return "19 - 20 tahun"
    if usia <= 22:
        return "21 - 22 tahun"
    return "23+ tahun"


def cari_terbesar(nilai_per_kategori):
    tertinggi = round(max(nilai_per_kategori[k] for k in KODE_KATEGORI), 2)
    if tertinggi <= 0:
        return []
    return [k for k in KODE_KATEGORI if round(nilai_per_kategori[k], 2) == tertinggi]


def buat_record(nilai, no_baris, id_mahasiswa, atribut=None):
    atribut = atribut or {}
    pengeluaran = {k: nilai[k] for k in KODE_KATEGORI}
    total = round(math.fsum(pengeluaran.values()), 2)
    pemasukan = nilai[KOLOM_PEMASUKAN]
    return {
        "id": id_mahasiswa,
        "baris": no_baris,
        "pemasukan": pemasukan,
        "pengeluaran": pengeluaran,
        "total_pengeluaran": total,
        "sisa": round(pemasukan - total, 2),
        "jurusan": atribut.get("jurusan") or "Tidak tercatat",
        "umur": atribut.get("umur") or "Tidak tercatat",
        "golongan_umur": kelompokkan_umur(atribut.get("umur")) or "Tidak tercatat",
        "gender": atribut.get("gender") or "Tidak tercatat",
    }


def muat_dataset(path):
    valid = []
    ditolak = []
    for urutan, (no_baris, baris) in enumerate(baca_baris_mentah(path), start=1):
        nilai, masalah = validasi_baris(baris)
        if masalah:
            ditolak.append({"baris": no_baris, "masalah": masalah})
        else:
            atribut = {
                kunci: ambil_teks_opsional(baris, daftar_alias)
                for kunci, daftar_alias in ALIAS_KOLOM_TAMBAHAN.items()
            }
            valid.append(buat_record(nilai, no_baris, ambil_id(baris, urutan), atribut))
    return valid, ditolak


def muat_ke_sesi(sesi, path):
    try:
        valid, ditolak = muat_dataset(path)
    except KesalahanData as galat:
        print("\n[Gagal Memuat Data] " + str(galat))
        return False
    sesi["path"] = path
    sesi["data"] = valid
    sesi["ditolak"] = ditolak
    if not valid:
        print("\n[Gagal Memproses Dataset] Semua baris ditolak saat validasi.")
        for item in ditolak[:5]:
            print(f"  - Baris {item['baris']}: " + "; ".join(item["masalah"]))
        return False
    return True


def rekap_data(data):
    if not data:
        raise KesalahanData("Tidak ada data valid yang dapat dihitung.")
    n = len(data)
    total_pemasukan = math.fsum(d["pemasukan"] for d in data)
    total_kategori = {k: math.fsum(d["pengeluaran"][k] for d in data) for k in KODE_KATEGORI}
    total_pengeluaran = math.fsum(total_kategori.values())
    per_kategori = {
        k: {
            "total": total_kategori[k],
            "rata": total_kategori[k] / n,
            "persen": hitung_persen(total_kategori[k], total_pengeluaran),
        }
        for k in KODE_KATEGORI
    }
    per_jenis = {
        jenis: {
            "total": math.fsum(total_kategori[k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == jenis),
            "persen": hitung_persen(
                math.fsum(total_kategori[k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == jenis),
                total_pengeluaran,
            ),
        }
        for jenis in DAFTAR_JENIS
    }
    return {
        "jumlah": n,
        "total_pemasukan": total_pemasukan,
        "total_pengeluaran": total_pengeluaran,
        "sisa": round(total_pemasukan - total_pengeluaran, 2),
        "rata_pemasukan": total_pemasukan / n,
        "rata_pengeluaran": total_pengeluaran / n,
        "per_kategori": per_kategori,
        "per_jenis": per_jenis,
        "jumlah_defisit": sum(1 for d in data if d["sisa"] < 0),
    }


def periksa_anggaran(persen):
    for k in KODE_KATEGORI:
        nilai = ke_angka(persen.get(k))
        if nilai is None:
            return False, "Persen untuk " + NAMA_KATEGORI[k] + " harus berupa angka."
        if nilai < 0 or nilai > 100:
            return False, "Persen untuk " + NAMA_KATEGORI[k] + " harus antara 0 sampai 100."
    total = math.fsum(float(persen[k]) for k in KODE_KATEGORI)
    if round(total, 6) > 100:
        return False, (
            "Total pembagian anggaran mencapai " + format(total, "g")
            + "%. Maksimal adalah 100% dari pemasukan."
        )
    return True, ""


def ringkas_perbandingan(daftar):
    anggaran = math.fsum(b["anggaran"] for b in daftar)
    realisasi = math.fsum(b["realisasi"] for b in daftar)
    selisih = round(anggaran - realisasi, 2)
    return {
        "anggaran": anggaran,
        "realisasi": realisasi,
        "selisih": selisih,
        "pemakaian": hitung_pemakaian(realisasi, anggaran),
        "status": status_anggaran(selisih),
    }


def bandingkan_anggaran(data, persen):
    if not data:
        raise KesalahanData("Tidak ada data valid untuk dibandingkan.")
    n = len(data)
    anggaran_mhs = [0.0] * n
    realisasi_mhs = [0.0] * n
    baris_banding = []
    for k in KODE_KATEGORI:
        total_anggaran = 0.0
        total_realisasi = 0.0
        jumlah_melebihi = 0
        for i, d in enumerate(data):
            anggaran = hitung_anggaran(d["pemasukan"], persen[k])
            realisasi = round(d["pengeluaran"][k], 2)
            total_anggaran += anggaran
            total_realisasi += realisasi
            anggaran_mhs[i] += anggaran
            realisasi_mhs[i] += realisasi
            if realisasi > anggaran:
                jumlah_melebihi += 1
        total_anggaran = round(total_anggaran, 2)
        total_realisasi = round(total_realisasi, 2)
        selisih = round(total_anggaran - total_realisasi, 2)
        baris_banding.append({
            "kode": k,
            "nama": NAMA_KATEGORI[k],
            "jenis": JENIS_KATEGORI[k],
            "anggaran": total_anggaran,
            "realisasi": total_realisasi,
            "selisih": selisih,
            "pemakaian": hitung_pemakaian(total_realisasi, total_anggaran),
            "status": status_anggaran(selisih),
            "jumlah_melebihi": jumlah_melebihi,
        })
    per_jenis = {
        jenis: ringkas_perbandingan([b for b in baris_banding if b["jenis"] == jenis])
        for jenis in DAFTAR_JENIS
    }
    melebihi_total = sum(
        1 for i in range(n) if round(realisasi_mhs[i], 2) > round(anggaran_mhs[i], 2)
    )
    return {
        "jumlah": n,
        "per_kategori": baris_banding,
        "per_jenis": per_jenis,
        "total": ringkas_perbandingan(baris_banding),
        "jumlah_melebihi_total": melebihi_total,
    }


def evaluasi_pengeluaran(rekap, banding):
    n = rekap["jumlah"]
    total_kategori = {k: rekap["per_kategori"][k]["total"] for k in KODE_KATEGORI}
    terbesar = cari_terbesar(total_kategori)
    urutan = sorted(KODE_KATEGORI, key=lambda k: total_kategori[k], reverse=True)
    tiga_terbesar = [k for k in urutan[:3] if total_kategori[k] > 0]
    melebihi = sorted(
        [b for b in banding["per_kategori"] if b["status"] == "MELEBIHI"],
        key=lambda b: b["selisih"],
    )
    dalam_anggaran = [b for b in banding["per_kategori"] if b["status"] != "MELEBIHI"]

    saran = []
    for b in melebihi[:3]:
        lebih = -b["selisih"]
        kalimat = "Coba kurangi pengeluaran " + b["nama"] + " sekitar " + format_angka(lebih)
        if n > 1:
            kalimat += " (rata-rata " + format_angka(lebih / n) + " per mahasiswa)"
        saran.append(kalimat + " agar kembali masuk batas anggaran.")
    if rekap["sisa"] < 0:
        nama_keinginan = ", ".join(
            NAMA_KATEGORI[k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == "Keinginan"
        )
        saran.append(
            "Total pengeluaran lebih besar dari pemasukan. Sebaiknya mulai pangkas pos Keinginan ("
            + nama_keinginan + ")."
        )
    if not saran:
        saran.append("Luar biasa! Semua pengeluaran masih aman di bawah batas anggaran. Pertahankan kebiasaan ini.")
    return {
        "terbesar": terbesar,
        "tiga_terbesar": tiga_terbesar,
        "melebihi": melebihi,
        "dalam_anggaran": dalam_anggaran,
        "saran": saran,
    }


def jalankan_analisis(data, persen):
    rekap = rekap_data(data)
    banding = bandingkan_anggaran(data, persen)
    return rekap, banding, evaluasi_pengeluaran(rekap, banding)


def hitung_regresi_linear(x_nilai, y_nilai):
    n = len(x_nilai)
    if n < 2 or len(y_nilai) != n:
        return None
    rata_x = math.fsum(x_nilai) / n
    rata_y = math.fsum(y_nilai) / n
    s_xx = math.fsum((x - rata_x) ** 2 for x in x_nilai)
    s_yy = math.fsum((y - rata_y) ** 2 for y in y_nilai)
    s_xy = math.fsum((x - rata_x) * (y - rata_y) for x, y in zip(x_nilai, y_nilai))
    if s_xx == 0:
        return None
    slope = s_xy / s_xx
    intercept = rata_y - slope * rata_x
    korelasi = 0.0 if s_yy == 0 else s_xy / math.sqrt(s_xx * s_yy)
    return {
        "n": n,
        "slope": slope,
        "intercept": intercept,
        "korelasi": korelasi,
        "r_kuadrat": korelasi ** 2,
        "rata_x": rata_x,
        "rata_y": rata_y,
    }


def bahasa_pola_hubungan(korelasi, label_x, label_y):
    kekuatan_persen = max(0.0, min(100.0, (korelasi ** 2) * 100))
    mutlak = abs(korelasi)
    tingkat = (
        "sangat terasa" if mutlak >= 0.7 else
        "cukup terasa" if mutlak >= 0.4 else
        "tidak terlalu kuat" if mutlak >= 0.2 else
        "hampir tidak saling memengaruhi"
    )
    if mutlak < 0.15:
        penjelasan = (
            f"Perubahan pada {label_x} {tingkat} terhadap {label_y}. "
            f"Artinya, naik-turunnya {label_y} lebih banyak dipengaruhi kebiasaan atau faktor lain."
        )
    elif korelasi > 0:
        penjelasan = (
            f"Hubungannya searah dan {tingkat}. Umumnya, saat {label_x} makin besar, "
            f"{label_y} juga cenderung ikut naik ({kekuatan_persen:.0f}% pergerakannya selaras dengan data ini)."
        )
    else:
        penjelasan = (
            f"Hubungannya berlawanan arah dan {tingkat}. Umumnya, saat {label_x} makin besar, "
            f"{label_y} justru cenderung lebih kecil ({kekuatan_persen:.0f}% pergerakannya selaras dengan data ini)."
        )
    return tingkat, penjelasan


def ambil_opsi_variabel(data):
    kebutuhan = [
        math.fsum(d["pengeluaran"][k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == "Kebutuhan")
        for d in data
    ]
    keinginan = [
        math.fsum(d["pengeluaran"][k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == "Keinginan")
        for d in data
    ]
    opsi = [
        ("income", "Pemasukan bulanan", [d["pemasukan"] for d in data]),
        ("total_exp", "Total pengeluaran bulanan", [d["total_pengeluaran"] for d in data]),
        ("sisa", "Sisa uang bulanan", [d["sisa"] for d in data]),
        ("kebutuhan", "Total pengeluaran kebutuhan pokok", kebutuhan),
        ("keinginan", "Total pengeluaran keinginan", keinginan),
    ]
    for k in KODE_KATEGORI:
        opsi.append((k, f"Pengeluaran {NAMA_KATEGORI[k].lower()}", [d["pengeluaran"][k] for d in data]))
    return opsi


def analisis_regresi_variabel(data):
    if len(data) < 2:
        raise KesalahanData("Minimal butuh 2 data mahasiswa agar pola hubungan bisa dihitung.")
    opsi = ambil_opsi_variabel(data)
    peta = {kode: (label, nilai) for kode, label, nilai in opsi}
    ringkasan = []
    for kode_x, kode_y in [
        ("income", "total_exp"),
        ("income", "kebutuhan"),
        ("income", "keinginan"),
        ("total_exp", "keinginan"),
    ]:
        nama_x, vx = peta[kode_x]
        nama_y, vy = peta[kode_y]
        hasil = hitung_regresi_linear(vx, vy)
        if hasil is not None:
            tingkat, penjelasan = bahasa_pola_hubungan(hasil["korelasi"], nama_x, nama_y)
            ringkasan.append((nama_x, nama_y, hasil, tingkat, penjelasan))
    return opsi, ringkasan


def tampilkan_sambutan(jumlah_data):
    garis("=")
    print("  SELAMAT DATANG DI APLIKASI KELOLA ANGGARAN MAHASISWA")
    garis("=")
    print("  Halo! Aplikasi ini siap membantu kamu memantau pemasukan, mengecek")
    print("  pengeluaran bulanan, melihat rekap per data, hingga membaca pola")
    print("  kebiasaan keuangan sehari-hari dengan bahasa yang mudah dipahami.")
    print()
    print(f"  [Info] Data keuangan berhasil disiapkan ({jumlah_data} data mahasiswa siap dianalisis).")
    garis("=")
    input("  Tekan [Enter] untuk masuk ke Menu Utama...")


def tampilkan_rekap(rekap):
    judul("RINGKASAN PEMASUKAN & PENGELUARAN (" + str(rekap["jumlah"]) + " MAHASISWA)")
    print("Petunjuk: Tabel ini menampilkan total seluruh uang masuk, uang keluar, serta")
    print("          pembagian pengeluaran berdasarkan kategori dan sifatnya (Kebutuhan/Keinginan).")
    garis()
    persen_defisit = hitung_persen(rekap["jumlah_defisit"], rekap["jumlah"])
    print(f"Total pemasukan                         : {format_angka(rekap['total_pemasukan'])}")
    print(f"Total pengeluaran                       : {format_angka(rekap['total_pengeluaran'])}")
    print(f"Sisa uang (pemasukan - pengeluaran)     : {format_angka(rekap['sisa'])}  [{status_kas(rekap['sisa'])}]")
    print(f"Rata-rata pemasukan per mahasiswa       : {format_angka(rekap['rata_pemasukan'])}")
    print(f"Rata-rata pengeluaran per mahasiswa     : {format_angka(rekap['rata_pengeluaran'])}")
    print(f"Mahasiswa yang pengeluarannya minus     : {rekap['jumlah_defisit']} dari {rekap['jumlah']} orang ({persen_defisit:.1f}%)")
    print()
    print(f"{'Kategori':<20}{'Sifat':<11}{'Total':>16}{'Rata-rata':>13}{'Porsi':>10}")
    garis()
    for k in KODE_KATEGORI:
        r = rekap["per_kategori"][k]
        print(f"{NAMA_KATEGORI[k]:<20}{JENIS_KATEGORI[k]:<11}{r['total']:>16,.2f}{r['rata']:>13,.2f}{r['persen']:>9.1f}%")
    garis()
    for jenis in DAFTAR_JENIS:
        r = rekap["per_jenis"][jenis]
        print(f"{'Total ' + jenis:<31}{r['total']:>16,.2f}{'':>13}{r['persen']:>9.1f}%")
    persen_total = hitung_persen(rekap["total_pengeluaran"], rekap["total_pengeluaran"])
    print(f"{'TOTAL SEMUA PENGELUARAN':<31}{rekap['total_pengeluaran']:>16,.2f}{rekap['rata_pengeluaran']:>13,.2f}{persen_total:>9.1f}%")


def tampilkan_tabel_mahasiswa(data):
    jumlah_halaman = (len(data) + BARIS_PER_HALAMAN - 1) // BARIS_PER_HALAMAN
    halaman = 0
    while True:
        judul(f"DAFTAR KEUANGAN PER MAHASISWA - Halaman {halaman + 1} dari {jumlah_halaman}")
        print("Petunjuk: Gunakan tombol di bawah tabel untuk berpindah halaman atau keluar.")
        garis()
        print(f"{'ID':<8}{'Baris':>7}{'Pemasukan':>14}{'Total Keluar':>20}{'Sisa / Minus':>17}{'Terpakai':>9}  Status")
        garis()
        awal = halaman * BARIS_PER_HALAMAN
        for d in data[awal:awal + BARIS_PER_HALAMAN]:
            rasio = hitung_persen(d["total_pengeluaran"], d["pemasukan"])
            print(
                f"{d['id']:<8}{d['baris']:>7}{d['pemasukan']:>14,.2f}"
                f"{d['total_pengeluaran']:>20,.2f}{d['sisa']:>17,.2f}{rasio:>8.1f}%  {status_kas(d['sisa'])}"
            )
        garis()
        pilihan = input(
            "Navigasi -> [Enter/N] Lanjut | [P] Sebelumnya | [Angka] Loncat halaman | [Q] Kembali ke menu: "
        ).strip().lower()
        nomor = ke_bilangan_bulat(pilihan)
        if pilihan in ("", "n"):
            if halaman >= jumlah_halaman - 1:
                return
            halaman += 1
        elif pilihan == "p":
            if halaman > 0:
                halaman -= 1
            else:
                print("[Info] Kamu sudah berada di halaman pertama.")
        elif pilihan == "q":
            return
        elif nomor is not None and 1 <= nomor <= jumlah_halaman:
            halaman = nomor - 1
        else:
            print("[Maaf] Perintah tidak dikenali. Silakan ketik N, P, nomor halaman, atau Q.")


def tampilkan_perbandingan(banding):
    judul("CEK REALISASI VS RENCANA ANGGARAN (" + str(banding["jumlah"]) + " MAHASISWA)")
    print("Petunjuk: Kolom 'Selisih' bernilai positif artinya masih ada sisa anggaran,")
    print("          sedangkan tanda minus (-) artinya pengeluaran sudah melebihi batas anggaran.")
    garis()
    print(f"{'Kategori':<20}{'Rencana':>15}{'Terpakai':>15}{'Selisih':>15}{'Serapan':>11}  {'Status':<9}{'Mhs Boros':>9}")
    garis()
    for b in banding["per_kategori"]:
        print(
            f"{b['nama']:<20}{b['anggaran']:>15,.2f}{b['realisasi']:>15,.2f}"
            f"{b['selisih']:>15,.2f}{format_persen(b['pemakaian']):>11}  {b['status']:<9}{b['jumlah_melebihi']:>9}"
        )
    garis()
    for jenis in DAFTAR_JENIS:
        s = banding["per_jenis"][jenis]
        print(
            f"{'Total ' + jenis:<20}{s['anggaran']:>15,.2f}{s['realisasi']:>15,.2f}"
            f"{s['selisih']:>15,.2f}{format_persen(s['pemakaian']):>11}  {s['status']:<9}"
        )
    t = banding["total"]
    print(
        f"{'TOTAL KESELURUHAN':<20}{t['anggaran']:>15,.2f}{t['realisasi']:>15,.2f}"
        f"{t['selisih']:>15,.2f}{format_persen(t['pemakaian']):>11}  {t['status']:<9}{banding['jumlah_melebihi_total']:>9}"
    )

    judul("KESIMPULAN SISA / KELEBIHAN ANGGARAN")
    print(f"Total anggaran yang direncanakan : {format_angka(t['anggaran'])}")
    print(f"Total uang yang benar terpakai   : {format_angka(t['realisasi'])}")
    if t["status"] == "SISA":
        print(f"Hasil akhir                      : HEMAT! Masih tersisa anggaran sebesar {format_angka(t['selisih'])}")
    elif t["status"] == "MELEBIHI":
        print(
            f"Hasil akhir                      : BOROS! Pengeluaran melebihi anggaran sebesar "
            f"{format_angka(-t['selisih'])} ({format_persen(t['pemakaian'])})"
        )
    else:
        print("Hasil akhir                      : PAS! Pengeluaran tepat sesuai rencana anggaran")
    persen_mhs = hitung_persen(banding["jumlah_melebihi_total"], banding["jumlah"])
    print(
        f"Jumlah mahasiswa yang over-budget: {banding['jumlah_melebihi_total']} "
        f"dari {banding['jumlah']} orang ({persen_mhs:.1f}%)"
    )


def tampilkan_evaluasi(rekap, banding, evaluasi):
    judul("EVALUASI & SARAN PENGHEMATAN")
    print("Petunjuk: Halaman ini merangkum kebocoran anggaran terbesar dan memberikan")
    print("          rekomendasi pos pengeluaran mana yang perlu dikurangi.")
    garis()
    terbesar = evaluasi["terbesar"]
    if terbesar:
        kode = terbesar[0]
        info = rekap["per_kategori"][kode]
        seri = " (seri)" if len(terbesar) > 1 else ""
        print(f"1. Pengeluaran paling besar       : {gabung_nama(terbesar)}{seri}")
        print(f"   Sebesar {format_angka(info['total'])} atau {info['persen']:.1f}% dari total pengeluaran")
        if len(evaluasi["tiga_terbesar"]) > 1:
            urutan = [
                NAMA_KATEGORI[k] + " (" + f"{rekap['per_kategori'][k]['persen']:.1f}%" + ")"
                for k in evaluasi["tiga_terbesar"]
            ]
            print("   3 Terbesar berturut-turut      : " + ", ".join(urutan))
    else:
        print("1. Pengeluaran paling besar       : Belum ada pengeluaran tercatat")

    melebihi = evaluasi["melebihi"]
    print(f"2. Pos yang melewati anggaran     : {len(melebihi)} dari {len(KODE_KATEGORI)} kategori")
    for b in melebihi:
        print(
            f"   - {b['nama']:<18} kelebihan {format_angka(-b['selisih']):>14}  "
            f"(terpakai {format_persen(b['pemakaian'])}, {b['jumlah_melebihi']} orang melebihi)"
        )
    if evaluasi["dalam_anggaran"]:
        print("3. Pos yang masih aman            : " + ", ".join(
            b["nama"] + " [" + b["status"] + " " + format_angka(b["selisih"]) + "]"
            for b in evaluasi["dalam_anggaran"]
        ))
    else:
        print("3. Pos yang masih aman            : Tidak ada yang aman")

    print(
        f"4. Kondisi keuangan umum          : {status_kas(rekap['sisa'])} "
        f"({rekap['jumlah_defisit']} dari {rekap['jumlah']} orang pengeluaran > pemasukan)"
    )
    kebutuhan = rekap["per_jenis"]["Kebutuhan"]["persen"]
    keinginan = rekap["per_jenis"]["Keinginan"]["persen"]
    print(f"5. Perbandingan gaya hidup        : Kebutuhan Pokok {kebutuhan:.1f}% | Keinginan {keinginan:.1f}%")
    print("6. Rekomendasi untuk kamu:")
    for kalimat in evaluasi["saran"]:
        print("   - " + kalimat)


def tampilkan_laporan(data, persen):
    rekap, banding, evaluasi = jalankan_analisis(data, persen)
    tampilkan_rekap(rekap)
    tampilkan_perbandingan(banding)
    tampilkan_evaluasi(rekap, banding, evaluasi)


def tampilkan_anggaran(anggaran):
    judul("PENGATURAN PERSENTASE RENCANA ANGGARAN")
    for nomor, k in enumerate(KODE_KATEGORI, start=1):
        print(f"{nomor}. {NAMA_KATEGORI[k]:<20}({JENIS_KATEGORI[k]:<9}) : {anggaran[k]:>6g}%")
    garis()
    total = math.fsum(float(anggaran[k]) for k in KODE_KATEGORI)
    print(f"   {'Total anggaran dialokasikan':<32}: {total:>6g}%")
    print(f"   {'Sisa untuk tabungan / cadangan':<32}: {100 - total:>6g}%")


def ubah_semua_anggaran_satu_baris(anggaran):
    print("\n--- UBAH SEMUA ANGGARAN SEKALIGUS (1 BARIS) ---")
    print("Masukkan 9 angka persentase secara berurutan dipisahkan SPASI atau KOMA.")
    print("Urutan: Tempat tinggal, Makanan, Transportasi, Kuliah, Hiburan, Pribadi, Teknologi, Kesehatan, Lainnya")
    print("Contoh: 30 10 5 5 10 2 8 3 7")
    teks = input("Masukkan 9 angka: ").strip()
    pemisah = "," if "," in teks else None
    potongan = [p.strip() for p in teks.split(pemisah) if p.strip()]
    if len(potongan) != len(KODE_KATEGORI):
        print(f"[Maaf] Kamu memasukkan {len(potongan)} angka. Harus tepat 9 angka sesuai urutan kategori.")
        return
    usulan = {}
    for k, item in zip(KODE_KATEGORI, potongan):
        nilai = ke_angka(item)
        if nilai is None:
            print(f"[Maaf] '{item}' pada kategori {NAMA_KATEGORI[k]} bukan angka yang valid.")
            return
        usulan[k] = nilai
    sah, pesan = periksa_anggaran(usulan)
    if sah:
        anggaran.update(usulan)
        print("[OK] Seluruh persentase anggaran berhasil diperbarui sekaligus!")
    else:
        print("[Maaf] " + pesan)


def atur_anggaran(anggaran):
    while True:
        tampilkan_anggaran(anggaran)
        print("\nPetunjuk Pengaturan:")
        print(" - Ketik angka [1 sampai 9] untuk mengubah satu kategori saja.")
        print(" - Ketik [S] untuk mengubah SEMUA kategori sekaligus dalam satu baris.")
        print(" - Ketik [R] untuk mengembalikan ke pengaturan awal (default).")
        print(" - Ketik [0] jika sudah selesai dan ingin kembali ke menu utama.")
        pilihan = input("\nMasukkan pilihan kamu: ").strip().lower()
        nomor = ke_bilangan_bulat(pilihan)
        if pilihan == "0":
            print("[OK] Pengaturan anggaran disimpan.")
            return
        if pilihan == "r":
            anggaran.clear()
            anggaran.update(ANGGARAN_DEFAULT_PERSEN)
            print("[OK] Anggaran berhasil dikembalikan ke pengaturan awal.")
        elif pilihan == "s":
            ubah_semua_anggaran_satu_baris(anggaran)
        elif nomor is not None and 1 <= nomor <= len(KODE_KATEGORI):
            kode = KODE_KATEGORI[nomor - 1]
            nilai = ke_angka(input(f"Masukkan persen baru untuk {NAMA_KATEGORI[kode]} (0-100): "))
            if nilai is None:
                print("[Maaf] Masukkan format angka yang benar, misalnya 12.5")
                continue
            usulan = dict(anggaran)
            usulan[kode] = nilai
            sah, pesan = periksa_anggaran(usulan)
            if sah:
                anggaran[kode] = nilai
                print(f"[OK] Anggaran {NAMA_KATEGORI[kode]} berhasil diubah menjadi {nilai:g}%.")
            else:
                print("[Maaf] " + pesan)
        else:
            print("[Maaf] Pilihan tidak dikenali. Ketik angka 1-9, S, R, atau 0.")


def analisis_satu_mahasiswa(sesi):
    judul("CEK KEUANGAN PER INDIVIDU")
    data = sesi["data"]
    print("Petunjuk: Masukkan nomor ID mahasiswa yang ingin dicek secara pribadi.")
    print(f"          ID yang tersedia di data saat ini mulai dari '{data[0]['id']}' sampai '{data[-1]['id']}'.")
    garis()
    id_cari = input("Ketik ID mahasiswa: ").strip()
    ditemukan = [d for d in data if d["id"] == id_cari]
    if not ditemukan:
        print(f"[Maaf] Data dengan ID '{id_cari}' tidak ditemukan.")
        return
    print(f"\nMenampilkan laporan khusus untuk Mahasiswa ID: {id_cari}")
    tampilkan_laporan([ditemukan[0]], sesi["anggaran"])


def trace_baris(sesi):
    judul("PENELUSURAN RINCIAN HITUNGAN (TRACING)")
    baris_mentah = baca_baris_mentah(sesi["path"])
    print("Petunjuk: Fitur ini memperlihatkan langkah demi langkah cara aplikasi menghitung")
    print("          satu baris data dari awal sampai akhir (cocok untuk lampiran laporan).")
    print(f"          Pilih nomor urut data antara 1 sampai {len(baris_mentah)}.")
    garis()
    urutan = ke_bilangan_bulat(input(f"Masukkan nomor urut data (1-{len(baris_mentah)}): "))
    if urutan is None or not 1 <= urutan <= len(baris_mentah):
        print("[Maaf] Nomor urut yang dimasukkan tidak valid.")
        return
    persen = sesi["anggaran"]
    no_baris, baris = baris_mentah[urutan - 1]
    judul(f"RINCIAN PERHITUNGAN DATA URUTAN KE-{urutan} (Baris {no_baris} di file)")

    print("[Tahap 1] Membaca data asli dari file")
    for kolom in KOLOM_WAJIB:
        print(f"    {kolom:<16}= {baris.get(kolom)!r}")

    print("[Tahap 2] Memeriksa kelengkapan dan kewajaran angka")
    nilai, masalah = validasi_baris(baris)
    if masalah:
        print("    Status: DATA DITOLAK karena ada kesalahan berikut:")
        for alasan in masalah:
            print("    - " + alasan)
        return
    print("    Status: DATA VALID & LOLOS PEMERIKSAAN")
    rec = buat_record(nilai, no_baris, ambil_id(baris, urutan))

    print("[Tahap 3] Menjumlahkan seluruh pos pengeluaran")
    total = 0.0
    print(f"    Awal hitungan = {total:,.2f}")
    for k in KODE_KATEGORI:
        total += rec["pengeluaran"][k]
        print(f"    + {NAMA_KATEGORI[k]:<18}({rec['pengeluaran'][k]:>9,.2f})  ->  Total sementara = {total:,.2f}")
    print(f"    Sisa uang = {rec['pemasukan']:,.2f} - {rec['total_pengeluaran']:,.2f} = {rec['sisa']:,.2f}  [{status_kas(rec['sisa'])}]")

    print("[Tahap 4] Membandingkan dengan jatah anggaran masing-masing pos")
    for k in KODE_KATEGORI:
        anggaran = hitung_anggaran(rec["pemasukan"], persen[k])
        realisasi = round(rec["pengeluaran"][k], 2)
        selisih = round(anggaran - realisasi, 2)
        print(
            f"    {NAMA_KATEGORI[k]:<18}: Jatah {anggaran:>9,.2f} | "
            f"Terpakai {realisasi:>9,.2f} | Selisih {selisih:>10,.2f} -> {status_anggaran(selisih)}"
        )

    print("[Tahap 5] Mencari pengeluaran paling besar")
    terbesar = cari_terbesar(rec["pengeluaran"])
    if terbesar:
        print(f"    Kategori terbesar adalah {gabung_nama(terbesar)} sebesar {rec['pengeluaran'][terbesar[0]]:,.2f}")
    else:
        print("    Tidak ada pengeluaran yang tercatat (semua 0)")


def tampilkan_regresi(data):
    opsi, ringkasan_bawaan = analisis_regresi_variabel(data)
    while True:
        judul("CEK POLA HUBUNGAN & PERKIRAAN PENGELUARAN")
        print("Petunjuk: Di sini kamu bisa melihat apakah dua hal dalam keuangan saling")
        print("          berkaitan (misalnya pemasukan dengan pengeluaran), atau mencoba")
        print("          mengira-ngira perkiraan pengeluaran jika suatu nilai diubah.")
        garis()
        print("Pola yang umum terlihat dari data saat ini:")
        for nomor, (nama_x, nama_y, _, tingkat, _) in enumerate(ringkasan_bawaan, start=1):
            print(f"  {nomor}. {nama_x.capitalize()} dan {nama_y} -> {tingkat}")
        garis()
        print("Mau coba fitur yang mana?")
        print("  [1] Cek pola hubungan antara dua hal pilihanmu sendiri")
        print("  [2] Coba hitung perkiraan nilai berdasarkan skenario angka tertentu")
        print("  [0] Kembali ke menu utama")
        pilihan = input("\nMasukkan pilihan kamu: ").strip().lower()
        if pilihan == "0":
            return
        if pilihan not in ("1", "2"):
            print("[Maaf] Pilihan tidak dikenali. Silakan ketik 1, 2, atau 0.")
            continue

        print("\nPilih dua hal yang ingin kamu cek:")
        for idx, (_, label, _) in enumerate(opsi, start=1):
            print(f"  {idx:>2}. {label.capitalize()}")
        idx_x = ke_bilangan_bulat(input("\nNomor hal pertama (yang dijadikan patokan/perubahan): "))
        idx_y = ke_bilangan_bulat(input("Nomor hal kedua (yang ingin dilihat perubahannya): "))
        if idx_x is None or not 1 <= idx_x <= len(opsi) or idx_y is None or not 1 <= idx_y <= len(opsi):
            print("[Maaf] Pilihan nomor belum sesuai. Coba pilih nomor yang ada di daftar.")
            continue
        if idx_x == idx_y:
            print("[Maaf] Pilih dua hal yang berbeda ya agar bisa dibandingkan.")
            continue

        _, label_x, vx = opsi[idx_x - 1]
        _, label_y, vy = opsi[idx_y - 1]
        hasil = hitung_regresi_linear(vx, vy)
        if hasil is None:
            print("[Info] Data patokan pada kelompok ini nilainya sama semua, jadi perubahannya belum bisa diukur.")
            continue

        _, penjelasan = bahasa_pola_hubungan(hasil["korelasi"], label_x, label_y)
        print("\n--- HASIL CEK POLA HUBUNGAN ---")
        print(f"Hal yang dibandingkan : {label_x.capitalize()}  -->  {label_y.capitalize()}")
        print(f"Kesimpulan pola      : {penjelasan}")
        print(
            f"Rata-rata {label_x} di data ini adalah {format_angka(hasil['rata_x'])}, "
            f"dengan rata-rata {label_y} {format_angka(hasil['rata_y'])}."
        )

        if pilihan == "2":
            x_uji = ke_angka(
                input(f"\nMasukkan perkiraan angka untuk '{label_x}' (rata-rata saat ini {format_angka(hasil['rata_x'])}): ")
            )
            if x_uji is None or abs(x_uji) > BATAS_ATAS_NILAI:
                print("[Maaf] Masukkan angka yang wajar ya, misalnya 1500 atau 2000.")
                continue
            y_prediksi = hasil["intercept"] + hasil["slope"] * x_uji
            print(
                f"\nPerkiraan '{label_y}' jika '{label_x}' berada di angka "
                f"{format_angka(x_uji)} adalah sekitar {format_angka(y_prediksi)}."
            )
            print("(Catatan: ini hanya gambaran kasar berdasarkan pola data yang ada, bukan patokan pasti.)")


def tampilkan_rekap_per_data(data):
    pilihan_data = [
        ("jurusan", "Jurusan"),
        ("umur", "Umur"),
        ("golongan_umur", "Golongan Umur"),
        ("gender", "Jenis Kelamin"),
    ]
    while True:
        judul("REKAP PER DATA")
        print("Petunjuk: Pilih jenis data untuk melihat rekapitulasi seluruh data yang ada.")
        garis()
        for nomor, (_, label) in enumerate(pilihan_data, start=1):
            print(f"  [{nomor}] Rekap per {label}")
        print("  [0] Kembali ke menu utama")
        garis()

        pilihan = ke_bilangan_bulat(input("Pilih nomor (0-4): "))
        if pilihan == 0:
            return
        if pilihan is None or not 1 <= pilihan <= len(pilihan_data):
            print("[Maaf] Pilihan belum sesuai. Silakan pilih 0 sampai 4.")
            continue

        kunci, label = pilihan_data[pilihan - 1]
        kelompok = {}
        for d in data:
            kelompok.setdefault(d[kunci], []).append(d)

        ringkasan = []
        for nama_grup, anggota in kelompok.items():
            n = len(anggota)
            total_masuk = math.fsum(a["pemasukan"] for a in anggota)
            total_keluar = math.fsum(a["total_pengeluaran"] for a in anggota)
            ringkasan.append({
                "kelompok": nama_grup,
                "jumlah": n,
                "rata_pemasukan": total_masuk / n,
                "total_pengeluaran": total_keluar,
                "rata_pengeluaran": total_keluar / n,
                "sisa": round(total_masuk - total_keluar, 2),
                "anggota": anggota,
            })
        ringkasan.sort(key=lambda item: (-item["total_pengeluaran"], item["kelompok"]))

        judul(f"REKAP PER {label.upper()} ({len(data)} DATA)")
        garis()
        print(f"{label:<28}{'Jumlah':>8}{'Rata Masuk':>15}{'Total Keluar':>16}{'Rata Keluar':>15}{'Sisa':>15}")
        garis()
        for r in ringkasan:
            print(
                f"{r['kelompok']:<28}{r['jumlah']:>8}{r['rata_pemasukan']:>15,.2f}"
                f"{r['total_pengeluaran']:>16,.2f}{r['rata_pengeluaran']:>15,.2f}{r['sisa']:>15,.2f}"
            )
        garis()

        if input("\nTampilkan rincian tiap data di dalamnya? [Y/T]: ").strip().lower() == "y":
            for r in ringkasan:
                print(f"\n[{r['kelompok']}] ({r['jumlah']} data)")
                for a in r["anggota"]:
                    print(
                        f"  - ID {a['id']} | Masuk: {format_angka(a['pemasukan'])} "
                        f"| Keluar: {format_angka(a['total_pengeluaran'])} | Sisa: {format_angka(a['sisa'])}"
                    )
        jeda_layar()


def tampilkan_menu():
    judul("MENU UTAMA - APLIKASI PENGELOLA ANGGARAN MAHASISWA")
    print("Silakan pilih layanan yang ingin kamu gunakan:")
    print("  [1] Lihat Ringkasan Pemasukan & Pengeluaran (Semua Mahasiswa)")
    print("  [2] Lihat Daftar Rincian per Mahasiswa (Tabel Halaman)")
    print("  [3] Atur Persentase Rencana Anggaran (Bisa ubah satu-satu atau sekaligus)")
    print("  [4] Cek Realisasi vs Rencana Anggaran (Cek pos yang hemat atau boros)")
    print("  [5] Lihat Evaluasi & Saran Penghematan")
    print("  [6] Cek Laporan Keuangan Satu Mahasiswa (Cari berdasarkan ID)")
    print("  [7] Lihat Rincian Langkah Perhitungan (Tracing data)")
    print("  [8] Cetak Laporan Lengkap (Gabungan menu 1, 4, dan 5)")
    print("  [9] Cek Pola Hubungan & Perkiraan Pengeluaran")
    print("  [10] Rekap per Data (Jurusan, Umur, Golongan Umur, Jenis Kelamin)")
    print("  [0] Keluar dari Aplikasi")
    garis()


def jalankan_menu(pilihan, sesi):
    data = sesi["data"]
    persen = sesi["anggaran"]
    if pilihan == "1":
        tampilkan_rekap(rekap_data(data))
        jeda_layar()
    elif pilihan == "2":
        tampilkan_tabel_mahasiswa(data)
    elif pilihan == "4":
        tampilkan_perbandingan(bandingkan_anggaran(data, persen))
        jeda_layar()
    elif pilihan == "5":
        rekap, banding, evaluasi = jalankan_analisis(data, persen)
        tampilkan_evaluasi(rekap, banding, evaluasi)
        jeda_layar()
    elif pilihan == "6":
        analisis_satu_mahasiswa(sesi)
        jeda_layar()
    elif pilihan == "7":
        trace_baris(sesi)
        jeda_layar()
    elif pilihan == "8":
        tampilkan_laporan(data, persen)
        jeda_layar()
    elif pilihan == "9":
        tampilkan_regresi(data)
    elif pilihan == "10":
        tampilkan_rekap_per_data(data)


def main():
    sesi = {
        "path": FILE_DEFAULT,
        "data": [],
        "ditolak": [],
        "anggaran": dict(ANGGARAN_DEFAULT_PERSEN),
    }
    path_awal = sys.argv[1] if len(sys.argv) > 1 else FILE_DEFAULT
    if not muat_ke_sesi(sesi, path_awal):
        print("Aplikasi tidak dapat dilanjutkan karena data gagal dimuat.")
        return

    tampilkan_sambutan(len(sesi["data"]))

    try:
        while True:
            tampilkan_menu()
            pilihan = input("Masukkan nomor menu pilihanmu (0-10): ").strip()
            try:
                if pilihan == "0":
                    print("\nTerima kasih telah menggunakan Aplikasi Pengelola Anggaran Mahasiswa. Sampai jumpa!")
                    break
                if pilihan == "3":
                    atur_anggaran(sesi["anggaran"])
                elif pilihan in ("1", "2", "4", "5", "6", "7", "8", "9", "10"):
                    jalankan_menu(pilihan, sesi)
                else:
                    print("[Maaf] Pilihan tidak tersedia. Silakan masukkan angka dari 0 sampai 10.")
            except KesalahanData as galat:
                print("[Terjadi Kendala] " + str(galat))
    except (KeyboardInterrupt, EOFError):
        print("\nAplikasi ditutup. Sampai jumpa!")


if __name__ == "__main__":
    main()