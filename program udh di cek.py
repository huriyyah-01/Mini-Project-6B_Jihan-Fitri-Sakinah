import csv
import math
import statistics

KATEGORI = [
    "housing", "food", "transportation", "books_supplies", "entertainment",
    "personal_care", "technology", "health_wellness", "miscellaneous",
]
WAJIB = ["monthly_income"] + KATEGORI
NAMA_INDO = {
    "housing": "Tempat tinggal", "food": "Makanan", "transportation": "Transportasi",
    "books_supplies": "Kebutuhan kuliah", "entertainment": "Hiburan",
    "personal_care": "Kebutuhan pribadi", "technology": "Teknologi",
    "health_wellness": "Kesehatan", "miscellaneous": "Lainnya",
}
KELOMPOK = {
    "housing": "Kebutuhan", "food": "Kebutuhan", "transportation": "Kebutuhan",
    "books_supplies": "Kebutuhan", "personal_care": "Kebutuhan", "health_wellness": "Kebutuhan",
    "entertainment": "Keinginan", "technology": "Keinginan", "miscellaneous": "Keinginan",
}
ANGGARAN_AWAL = {
    "housing": 30, "food": 10, "transportation": 5, "books_supplies": 5,
    "personal_care": 5, "health_wellness": 5, "entertainment": 10, "technology": 10, "miscellaneous": 5,
}


def baca_data(nama_file):
    bersih = nama_file.strip()
    if not bersih:
        print("Nama file belum diisi.")
        return [], []
    data_oke, baris_gagal = [], []
    try:
        with open(bersih, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("File CSV kosong atau ga ada header.")
                return [], []
            kolom_map = {h.strip().lower(): h for h in reader.fieldnames if h is not None}
            kurang = [k for k in WAJIB if k not in kolom_map]
            if kurang:
                print("Kolom wajib tidak lengkap:", ", ".join(kurang))
                return [], []
            for no_baris, row in enumerate(reader, start=2):
                angka_row, lolos = {}, True
                for k in WAJIB:
                    raw_val = str(row.get(kolom_map[k], "")).strip()
                    if raw_val == "":
                        lolos = False
                        break
                    try:
                        val = float(raw_val)
                    except ValueError:
                        lolos = False
                        break
                    if not math.isfinite(val) or val < 0:
                        lolos = False
                        break
                    angka_row[k] = val
                if lolos and angka_row["monthly_income"] <= 0:
                    lolos = False
                if lolos:
                    keluar_per_kat = {k: angka_row[k] for k in KATEGORI}
                    data_oke.append({"masuk": angka_row["monthly_income"], "keluar": keluar_per_kat, "total": round(sum(keluar_per_kat.values()), 2)})
                else:
                    baris_gagal.append(no_baris)
    except FileNotFoundError:
        print(f"File '{bersih}' File csv tidak ditemukan, cek lagi nama atau foldernya.")
    return data_oke, baris_gagal


def olah_keuangan(data, persen):
    total_masuk = round(sum(d["masuk"] for d in data), 2)
    total_kat = {k: round(sum(d["keluar"][k] for d in data), 2) for k in KATEGORI}
    total_keluar = round(sum(total_kat.values()), 2)
    ringkas_jenis = {
        jenis: (
            round(sum(total_kat[k] for k in KATEGORI if KELOMPOK[k] == jenis), 2),
            (sum(total_kat[k] for k in KATEGORI if KELOMPOK[k] == jenis) / total_keluar * 100) if total_keluar > 0 else 0.0,
        )
        for jenis in ("Kebutuhan", "Keinginan")
    }
    perbandingan = []
    for k in KATEGORI:
        rencana = round(sum(round(d["masuk"] * persen[k] / 100, 2) for d in data), 2)
        aktual = total_kat[k]
        selisih = round(rencana - aktual, 2)
        status = "SISA" if selisih > 0 else ("MELEBIHI" if selisih < 0 else "PAS")
        perbandingan.append((k, rencana, aktual, selisih, status))
    total_rencana = round(sum(item[1] for item in perbandingan), 2)
    return {
        "jumlah_mhs": len(data), "total_masuk": total_masuk, "total_keluar": total_keluar,
        "sisa_uang": round(total_masuk - total_keluar, 2),
        "rata_keluar": round(statistics.mean(d["total"] for d in data), 2),
        "total_kat": total_kat, "ringkas_jenis": ringkas_jenis, "perbandingan": perbandingan,
        "total_rencana": total_rencana, "selisih_total": round(total_rencana - total_keluar, 2),
        "kat_terbesar": max(KATEGORI, key=lambda k: total_kat[k]) if total_keluar > 0 else "",
    }


def cetak_rekap(hasil, persen):
    pemisah = "-" * 66
    print(f"\n=== REKAP PENGELUARAN ({hasil['jumlah_mhs']} MAHASISWA) ===")
    print(f"Total Pemasukan  : {hasil['total_masuk']:>14,.2f}")
    print(f"Total Pengeluaran: {hasil['total_keluar']:>14,.2f}  (Rata-rata: {hasil['rata_keluar']:,.2f})")
    print(f"Sisa Uang        : {hasil['sisa_uang']:>14,.2f}")
    print(f"Target Anggaran  : {hasil['total_rencana']:>14,.2f}  (Selisih: {hasil['selisih_total']:+,.2f})")
    print(pemisah)
    print(f"{'Kategori':<18} {'Kelompok':<10} {'Total':>14} {'Porsi':>8} {'Target%':>7}")
    print(pemisah)
    for k in KATEGORI:
        porsi = (hasil["total_kat"][k] / hasil["total_keluar"] * 100) if hasil["total_keluar"] > 0 else 0.0
        print(f"{NAMA_INDO[k]:<18} {KELOMPOK[k]:<10} {hasil['total_kat'][k]:>14,.2f} {porsi:>7.1f}% {persen[k]:>6g}%")
    print(pemisah)
    for jenis, (tot_j, p_j) in hasil["ringkas_jenis"].items():
        print(f"{'Subtotal ' + jenis:<29} {tot_j:>14,.2f} {p_j:>7.1f}%")
    print(pemisah)


def cetak_anggaran_evaluasi(hasil):
    pemisah = "-" * 72
    print("\n=== PERBANDINGAN ANGGARAN & REALISASI ===")
    print(f"{'Kategori':<18} {'Anggaran':>13} {'Realisasi':>13} {'Selisih':>13} {'Status':<10}")
    print(pemisah)
    for k, rencana, aktual, selisih, status in hasil["perbandingan"]:
        print(f"{NAMA_INDO[k]:<18} {rencana:>13,.2f} {aktual:>13,.2f} {selisih:>13,.2f} {status:<10}")
    print(pemisah)
    ket = f"SISA {hasil['selisih_total']:,.2f}" if hasil["selisih_total"] >= 0 else f"LEBIH {-hasil['selisih_total']:,.2f}"
    print(f"{'TOTAL':<18} {hasil['total_rencana']:>13,.2f} {hasil['total_keluar']:>13,.2f} {hasil['selisih_total']:>13,.2f} [{ket}]")
    print(pemisah)
    print("\n EVALUASI ")
    if hasil["kat_terbesar"]:
        kb = hasil["kat_terbesar"]
        print(f"Pengeluaran terbesar : {NAMA_INDO[kb]} ({hasil['total_kat'][kb]:,.2f})")
    boros = [NAMA_INDO[b[0]] for b in hasil["perbandingan"] if b[4] == "MELEBIHI"]
    print(f"Melebihi anggaran    : {', '.join(boros) if boros else 'Tidak ada'}")


def ubah_anggaran(persen):
    print("\n UBAH PERSEN ANGGARAN ")
    for nomor, k in enumerate(KATEGORI, start=1):
        print(f"{nomor}. {NAMA_INDO[k]:<18}: {persen[k]:>5g}%")
    try:
        pilihan_kat = int(input("Nomor kategori (0 untuk batal): ").strip())
        if pilihan_kat == 0 or not (1 <= pilihan_kat <= len(KATEGORI)):
            return
        nilai_baru = float(input("Persen baru (0-100): ").strip().replace(",", "."))
    except ValueError:
        print("Masukkan angka yang valid (0-100).")
        return
    if not math.isfinite(nilai_baru) or not (0 <= nilai_baru <= 100):
        print("Persen harus diantara 0 sampai 100.")
        return
    kode_kat = KATEGORI[pilihan_kat - 1]
    if round(sum(persen.values()) - persen[kode_kat] + nilai_baru, 6) > 100:
        print("Total seluruh persen anggaran tidak boleh lewat 100%.")
        return
    persen[kode_kat] = nilai_baru
    print(f"Anggaran {NAMA_INDO[kode_kat]} sekarang {nilai_baru:g}%.")


def main():
    persen = dict(ANGGARAN_AWAL)
    data, ditolak = [], []
    while True:
        print("\n[1] Muat CSV  [2] Rekap  [3] Anggaran & Evaluasi  [4] Ubah Anggaran  [0] Keluar")
        menu = input("Pilih menu: ").strip()
        if menu == "0":
            print("Selesai.")
            break
        elif menu == "1":
            nama_file = input("Nama atau path file CSV: ").strip()
            data, ditolak = baca_data(nama_file)
            if data:
                print(f"Berhasil dimuat: {len(data)} data valid, {len(ditolak)} baris ditolak.")
        elif menu == "4":
            ubah_anggaran(persen)
        elif menu in ("2", "3"):
            if not data:
                print("pilih file terlebih dahulu.")
                continue
            hasil = olah_keuangan(data, persen)
            cetak_rekap(hasil, persen) if menu == "2" else cetak_anggaran_evaluasi(hasil)
        else:
            print("pilih menu yang ada aja.")


if __name__ == "__main__":
    main()