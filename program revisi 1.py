import csv
import math
import os
import sys

try:
    FOLDER_PROGRAM = os.path.dirname(os.path.abspath(__file__))
except NameError:
    FOLDER_PROGRAM = os.getcwd()


FILE_DEFAULT = "student_spending_Rp_rapi.csv"
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

BATAS_ATAS_NILAI = 1_000_000_000
BARIS_PER_HALAMAN = 10


class KesalahanData(Exception):
    pass


def format_angka(nilai):
    return f"{nilai:,.2f}"


def format_persen(nilai):
    return "-" if nilai is None else f"{nilai:.1f}%"


def hitung_persen(bagian, total):
    if total == 0:
        return 0.0
    return bagian / total * 100


def ke_bilangan_bulat(teks):
    try:
        return int(teks.strip())
    except ValueError:
        return None


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
    if anggaran == 0:
        return None
    return realisasi / anggaran * 100


def gabung_nama(kode_kategori):
    return " dan ".join(NAMA_KATEGORI[k] for k in kode_kategori)


def jeda_layar():
    input("\nTekan [Enter] untuk kembali ke menu utama...")


def cari_file(path):
    nama = str(path).strip().strip('"').strip("'")
    if nama == "":
        raise KesalahanData("Nama file data belum diisi.")
    for lokasi in (nama, os.path.join(FOLDER_PROGRAM, nama)):
        if os.path.isfile(lokasi):
            return lokasi
    raise KesalahanData("Maaf, file '" + nama + "' tidak ditemukan. Pastikan file ada di folder yang sama dengan aplikasi ini.")


def baca_baris_mentah(path):
    lokasi = cari_file(path)
    hasil = []
    try:
        with open(lokasi, newline="", encoding="utf-8-sig") as berkas:
            pembaca = csv.reader(berkas)
            baris_header = next(pembaca, None)
            if baris_header is None or not any(sel.strip() for sel in baris_header):
                raise KesalahanData("File data kosong dan tidak memiliki isi.")
            header = [sel.strip().lower() for sel in baris_header]
            hilang = [kolom for kolom in KOLOM_WAJIB if kolom not in header]
            if hilang:
                raise KesalahanData("Format file tidak sesuai, kolom berikut tidak ditemukan: " + ", ".join(hilang))
            for isi in pembaca:
                if not isi:
                    continue
                baris = {}
                for i, nama_kolom in enumerate(header):
                    baris[nama_kolom] = isi[i] if i < len(isi) else None
                hasil.append((pembaca.line_num, baris))
    except PermissionError:
        raise KesalahanData("Aplikasi tidak memiliki izin untuk membuka file '" + str(path) + "'.")
    except UnicodeDecodeError:
        raise KesalahanData("File tidak dapat dibaca. Pastikan file berformat CSV standar.")
    except csv.Error as galat:
        raise KesalahanData("Terjadi kerusakan format di dalam file CSV: " + str(galat))
    except OSError as galat:
        raise KesalahanData("File gagal dibuka: " + str(galat))
    if not hasil:
        raise KesalahanData("File hanya berisi judul kolom tanpa ada data transaksi di dalamnya.")
    return hasil


def validasi_baris(baris):
    nilai = {}
    masalah = []
    for kolom in KOLOM_WAJIB:
        teks = baris.get(kolom)
        if teks is None or teks.strip() == "":
            masalah.append(kolom + ": data kosong")
            continue
        teks = teks.strip()
        try:
            angka = float(teks)
        except ValueError:
            masalah.append(kolom + ": bukan angka ('" + teks + "')")
            continue
        if not math.isfinite(angka):
            masalah.append(kolom + ": angka tidak valid ('" + teks + "')")
        elif angka < 0:
            masalah.append(kolom + ": bernilai minus (" + teks + ")")
        elif angka > BATAS_ATAS_NILAI:
            masalah.append(kolom + ": angka terlalu besar (" + teks + ")")
        else:
            nilai[kolom] = angka
    if nilai.get(KOLOM_PEMASUKAN) == 0:
        masalah.append(KOLOM_PEMASUKAN + ": pemasukan bernilai 0")
    if masalah:
        return None, masalah
    return nilai, []


def ambil_id(baris, urutan):
    for kolom in KOLOM_ID:
        teks = baris.get(kolom)
        if teks is not None and teks.strip() != "":
            return teks.strip()
    return str(urutan)


def buat_record(nilai, no_baris, id_mahasiswa):
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
    }


def muat_dataset(path):
    valid = []
    ditolak = []
    for urutan, (no_baris, baris) in enumerate(baca_baris_mentah(path), start=1):
        nilai, masalah = validasi_baris(baris)
        if masalah:
            ditolak.append({"baris": no_baris, "masalah": masalah})
        else:
            valid.append(buat_record(nilai, no_baris, ambil_id(baris, urutan)))
    return valid, ditolak


def rekap_data(data):
    if not data:
        raise KesalahanData("Tidak ada data valid yang dapat dihitung.")
    n = len(data)
    total_pemasukan = math.fsum(d["pemasukan"] for d in data)
    total_kategori = {
        k: math.fsum(d["pengeluaran"][k] for d in data) for k in KODE_KATEGORI
    }
    total_pengeluaran = math.fsum(total_kategori.values())

    per_kategori = {}
    for k in KODE_KATEGORI:
        per_kategori[k] = {
            "total": total_kategori[k],
            "rata": total_kategori[k] / n,
            "persen": hitung_persen(total_kategori[k], total_pengeluaran),
        }
    per_jenis = {}
    for jenis in DAFTAR_JENIS:
        total_jenis = math.fsum(
            total_kategori[k] for k in KODE_KATEGORI if JENIS_KATEGORI[k] == jenis
        )
        per_jenis[jenis] = {
            "total": total_jenis,
            "persen": hitung_persen(total_jenis, total_pengeluaran),
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
        try:
            nilai = float(persen[k])
        except (KeyError, TypeError, ValueError):
            return False, "Persen untuk " + NAMA_KATEGORI[k] + " harus berupa angka."
        if not math.isfinite(nilai) or nilai < 0 or nilai > 100:
            return False, "Persen untuk " + NAMA_KATEGORI[k] + " harus antara 0 sampai 100."
    total = math.fsum(float(persen[k]) for k in KODE_KATEGORI)
    if round(total, 6) > 100:
        return False, "Total pembagian anggaran mencapai " + format(total, "g") + "%. Maksimal adalah 100% dari pemasukan."
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


def cari_terbesar(nilai_per_kategori):
    tertinggi = round(max(nilai_per_kategori[k] for k in KODE_KATEGORI), 2)
    if tertinggi <= 0:
        return []
    return [k for k in KODE_KATEGORI if round(nilai_per_kategori[k], 2) == tertinggi]


def evaluasi_pengeluaran(rekap, banding):
    n = rekap["jumlah"]
    total_kategori = {k: rekap["per_kategori"][k]["total"] for k in KODE_KATEGORI}
    terbesar = cari_terbesar(total_kategori)
    urutan = sorted(KODE_KATEGORI, key=lambda k: total_kategori[k], reverse=True)
    tiga_terbesar = [k for k in urutan[:3] if total_kategori[k] > 0]

    melebihi = [b for b in banding["per_kategori"] if b["status"] == "MELEBIHI"]
    melebihi.sort(key=lambda b: b["selisih"])
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
            "Total pengeluaran lebih besar dari pemasukan. Sebaiknya mulai pangkas pos Keinginan (" + nama_keinginan + ")."
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
    evaluasi = evaluasi_pengeluaran(rekap, banding)
    return rekap, banding, evaluasi


def garis(karakter="-", lebar=100):
    print(karakter * lebar)


def judul(teks):
    print()
    garis("=")
    print("  " + teks)
    garis("=")


def tampilkan_sambutan(jumlah_data):
    garis("=")
    print("  SELAMAT DATANG DI APLIKASI KELOLA ANGGARAN MAHASISWA")
    garis("=")
    print("  Halo! Aplikasi ini siap membantu kamu memantau pemasukan, mengecek")
    print("  pengeluaran bulanan, serta melihat pos mana saja yang paling boros.")
    print("  Kamu tidak perlu paham pemrograman, cukup pilih menu yang tersedia.")
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
        label = "Total " + jenis
        print(f"{label:<31}{r['total']:>16,.2f}{'':>13}{r['persen']:>9.1f}%")
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
            print(f"{d['id']:<8}{d['baris']:>7}{d['pemasukan']:>14,.2f}{d['total_pengeluaran']:>20,.2f}{d['sisa']:>17,.2f}{rasio:>8.1f}%  {status_kas(d['sisa'])}")
        garis()
        pilihan = input("Navigasi -> [Enter/N] Lanjut | [P] Sebelumnya | [Angka] Loncat halaman | [Q] Kembali ke menu: ").strip().lower()
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
        print(f"{b['nama']:<20}{b['anggaran']:>15,.2f}{b['realisasi']:>15,.2f}{b['selisih']:>15,.2f}{format_persen(b['pemakaian']):>11}  {b['status']:<9}{b['jumlah_melebihi']:>9}")
    garis()
    for jenis in DAFTAR_JENIS:
        s = banding["per_jenis"][jenis]
        label = "Total " + jenis
        print(f"{label:<20}{s['anggaran']:>15,.2f}{s['realisasi']:>15,.2f}{s['selisih']:>15,.2f}{format_persen(s['pemakaian']):>11}  {s['status']:<9}")
    t = banding["total"]
    print(f"{'TOTAL KESELURUHAN':<20}{t['anggaran']:>15,.2f}{t['realisasi']:>15,.2f}{t['selisih']:>15,.2f}{format_persen(t['pemakaian']):>11}  {t['status']:<9}{banding['jumlah_melebihi_total']:>9}")

    judul("KESIMPULAN SISA / KELEBIHAN ANGGARAN")
    print(f"Total anggaran yang direncanakan : {format_angka(t['anggaran'])}")
    print(f"Total uang yang benar terpakai   : {format_angka(t['realisasi'])}")
    if t["status"] == "SISA":
        print(f"Hasil akhir                      : HEMAT! Masih tersisa anggaran sebesar {format_angka(t['selisih'])}")
    elif t["status"] == "MELEBIHI":
        print(f"Hasil akhir                      : BOROS! Pengeluaran melebihi anggaran sebesar {format_angka(-t['selisih'])} ({format_persen(t['pemakaian'])})")
    else:
        print("Hasil akhir                      : PAS! Pengeluaran tepat sesuai rencana anggaran")
    persen_mhs = hitung_persen(banding["jumlah_melebihi_total"], banding["jumlah"])
    print(f"Jumlah mahasiswa yang over-budget: {banding['jumlah_melebihi_total']} dari {banding['jumlah']} orang ({persen_mhs:.1f}%)")


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
            urutan = [NAMA_KATEGORI[k] + " (" + f"{rekap['per_kategori'][k]['persen']:.1f}%" + ")" for k in evaluasi["tiga_terbesar"]]
            print("   3 Terbesar berturut-turut      : " + ", ".join(urutan))
    else:
        print("1. Pengeluaran paling besar       : Belum ada pengeluaran tercatat")

    melebihi = evaluasi["melebihi"]
    print(f"2. Pos yang melewati anggaran     : {len(melebihi)} dari {len(KODE_KATEGORI)} kategori")
    for b in melebihi:
        print(f"   - {b['nama']:<18} kelebihan {format_angka(-b['selisih']):>14}  (terpakai {format_persen(b['pemakaian'])}, {b['jumlah_melebihi']} orang melebihi)")
    if evaluasi["dalam_anggaran"]:
        print("3. Pos yang masih aman            : " + ", ".join(
            b["nama"] + " [" + b["status"] + " " + format_angka(b["selisih"]) + "]" for b in evaluasi["dalam_anggaran"]))
    else:
        print("3. Pos yang masih aman            : Tidak ada yang aman")

    print(f"4. Kondisi keuangan umum          : {status_kas(rekap['sisa'])} ({rekap['jumlah_defisit']} dari {rekap['jumlah']} orang pengeluaran > pemasukan)")
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
            print("\n--- UBAH SEMUA ANGGARAN SEKALIGUS (1 BARIS) ---")
            print("Masukkan 9 angka persentase secara berurutan dipisahkan SPASI atau KOMA.")
            print("Urutan: Tempat tinggal, Makanan, Transportasi, Kuliah, Hiburan, Pribadi, Teknologi, Kesehatan, Lainnya")
            print("Contoh: 30 10 5 5 10 2 8 3 7")
            teks = input("Masukkan 9 angka: ").strip()
            pemisah = "," if "," in teks else None
            potongan = [p.strip() for p in teks.split(pemisah) if p.strip()]
            if len(potongan) != len(KODE_KATEGORI):
                print(f"[Maaf] Kamu memasukkan {len(potongan)} angka. Harus tepat 9 angka sesuai urutan kategori.")
                continue
            usulan = {}
            valid_angka = True
            for k, item in zip(KODE_KATEGORI, potongan):
                try:
                    usulan[k] = float(item)
                except ValueError:
                    print(f"[Maaf] '{item}' pada kategori {NAMA_KATEGORI[k]} bukan angka yang valid.")
                    valid_angka = False
                    break
            if not valid_angka:
                continue
            sah, pesan = periksa_anggaran(usulan)
            if sah:
                anggaran.update(usulan)
                print("[OK] Seluruh persentase anggaran berhasil diperbarui sekaligus!")
            else:
                print("[Maaf] " + pesan)
        elif nomor is not None and 1 <= nomor <= len(KODE_KATEGORI):
            kode = KODE_KATEGORI[nomor - 1]
            teks = input(f"Masukkan persen baru untuk {NAMA_KATEGORI[kode]} (0-100): ").strip().replace(",", ".")
            try:
                nilai = float(teks)
            except ValueError:
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


def muat_ke_sesi(sesi, path):
    try:
        valid, ditolak = muat_dataset(path)
    except KesalahanData as galat:
        print("\n[Gagal Memuat Data] " + str(galat))
        return False
    sesi["path"] = path
    sesi["data"] = valid
    sesi["ditolak"] = ditolak
    return bool(valid)


def analisis_satu_mahasiswa(sesi):
    judul("CEK KEUANGAN PER INDIVIDU")
    data = sesi["data"]
    print(f"Petunjuk: Masukkan nomor ID mahasiswa yang ingin dicek secara pribadi.")
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
    print(f"Petunjuk: Fitur ini memperlihatkan langkah demi langkah cara aplikasi menghitung")
    print(f"          satu baris data dari awal sampai akhir (cocok untuk lampiran laporan).")
    print(f"          Pilih nomor urut data antara 1 sampai {len(baris_mentah)}.")
    garis()
    teks = input(f"Masukkan nomor urut data (1-{len(baris_mentah)}): ")
    urutan = ke_bilangan_bulat(teks)
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
        print(f"    {NAMA_KATEGORI[k]:<18}: Jatah {anggaran:>9,.2f} | Terpakai {realisasi:>9,.2f} | Selisih {selisih:>10,.2f} -> {status_anggaran(selisih)}")

    print("[Tahap 5] Mencari pengeluaran paling besar")
    terbesar = cari_terbesar(rec["pengeluaran"])
    if terbesar:
        print(f"    Kategori terbesar adalah {gabung_nama(terbesar)} sebesar {rec['pengeluaran'][terbesar[0]]:,.2f}")
    else:
        print("    Tidak ada pengeluaran yang tercatat (semua 0)")


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
            pilihan = input("Masukkan nomor menu pilihanmu (0-8): ").strip()
            try:
                if pilihan == "0":
                    print("\nTerima kasih telah menggunakan Aplikasi Pengelola Anggaran Mahasiswa. Sampai jumpa!")
                    break
                if pilihan == "3":
                    atur_anggaran(sesi["anggaran"])
                elif pilihan in ("1", "2", "4", "5", "6", "7", "8"):
                    jalankan_menu(pilihan, sesi)
                else:
                    print("[Maaf] Pilihan tidak tersedia. Silakan masukkan angka dari 0 sampai 8.")
            except KesalahanData as galat:
                print("[Terjadi Kendala] " + str(galat))
    except (KeyboardInterrupt, EOFError):
        print("\nAplikasi ditutup. Sampai jumpa!")


if __name__ == "__main__":
    main()