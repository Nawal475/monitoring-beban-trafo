"""
Import data gardu PLN dari Excel ke SQLite
"""

import pandas as pd
import sqlite3

FILE_PATH = "DATA GARDU.xlsx"


def main():

    print("Membaca file Excel...")

    raw = pd.read_excel(
        FILE_PATH,
        header=None
    )

    start_idx = None

    for i in range(len(raw)):

        try:
            int(raw.iloc[i, 0])
            start_idx = i
            break

        except:
            pass

    if start_idx is None:
        raise Exception("Data gardu tidak ditemukan.")

    print("Data dimulai pada baris:", start_idx)

    df = raw.iloc[start_idx:].reset_index(drop=True)

    df = df[
        df[0].apply(
            lambda x:
            str(x).replace(".0", "").isdigit()
            if pd.notna(x)
            else False
        )
    ]

    print("Jumlah gardu:", len(df))

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM gardu")

    berhasil = 0

    for _, row in df.iterrows():

        def val(col):

            if col >= len(row):
                return None

            v = row[col]

            if pd.isna(v):
                return None

            return v

        try:

            cur.execute("""
            INSERT INTO gardu
            (
                no_urut,
                gi_trafo,
                penyulang,
                nama_gardu,
                pemakaian,
                uraian_nama,
                jenis,
                type_gardu,
                no_gardu,
                wilayah_kerja,
                daya_kva_pln,
                daya_kva_plgn,
                merk_trafo,
                no_seri,
                tahun,
                jml_phbtr_rak_tr,
                jml_jurusan,
                merk_cubicle,
                type_cubicle,
                fasa,
                keterangan,
                tgl_terakhir_dipelihara
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """, (

                val(0),
                val(1),
                val(2),
                val(3),
                val(5),
                val(6),
                val(7),
                val(8),
                val(9),
                val(10),
                val(11),
                val(12),
                val(13),
                val(14),
                val(15),
                val(16),
                val(17),
                val(18),
                val(19),
                val(29),
                val(30),
                val(32)

            ))

            berhasil += 1

        except Exception as e:

            print("Lewati:", e)

    conn.commit()

    cur.close()
    conn.close()

    print("Import selesai.")
    print("Jumlah gardu:", berhasil)


if __name__ == "__main__":
    main()