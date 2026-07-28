from flask import Flask, render_template, request, redirect, session, send_file
from datetime import date, datetime
import psycopg2
import os
import io
import pandas as pd
from openpyxl import Workbook
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "pln123"

@app.context_processor
def inject_user():
    return {
        "username": session.get("username", "Admin")
    }

# KONEKSI NEON
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode="require"
    )

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                nama,
                username,
                password,
                role
            FROM users
            WHERE username=%s
        """, (username,))

        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and user[3] == password:

            session["user_id"] = user[0]
            session["nama"] = user[1]
            session["username"] = user[2]
            session["role"] = user[4]

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Username atau password salah!"
        )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/users")
def users():

    if "username" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            nama,
            email,
            username,
            role
        FROM users
        ORDER BY id
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "users.html",
        users=users,
        username=session["username"]
    )

@app.route("/hapus_user/<int:id>")
def hapus_user(id):

    if "username" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = get_connection()
    cur = conn.cursor()

    # Admin tidak boleh menghapus dirinya sendiri
    cur.execute("""
        SELECT username
        FROM users
        WHERE id=%s
    """, (id,))

    user = cur.fetchone()

    if user and user[0] == session["username"]:

        cur.close()
        conn.close()

        return redirect("/users")

    cur.execute("""
        DELETE FROM users
        WHERE id=%s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect("/users")

@app.route("/edit_user/<int:id>", methods=["GET","POST"])
def edit_user(id):

    if "username" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = get_connection()
    cur = conn.cursor()

    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form.get("password")
        role = request.form["role"]

        cur.execute("""
            UPDATE users
            SET
                nama=%s,
                email=%s,
                username=%s,
                password=%s,
                role=%s
            WHERE id=%s
        """,(
            nama,
            email,
            username,
            password,
            role,
            id
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/users")

    cur.execute("""
        SELECT
            id,
            nama,
            email,
            username,
            role
        FROM users
        WHERE id=%s
    """,(id,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "edit_user.html",
        user=user
    )

@app.route("/download_pembebanan")
def download_pembebanan():

    if "username" not in session:
        return redirect("/")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM riwayat_pembebanan
        ORDER BY id DESC
    """)

    data = cur.fetchall()

    header = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Pembebanan"

    ws.append(header)

    for row in data:
        ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="Laporan_Pembebanan.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Konfirmasi password tidak sesuai!"
            )

        conn = get_connection()
        cur = conn.cursor()

        # cek username

        cur.execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

        if cur.fetchone():

            cur.close()
            conn.close()

            return render_template(
                "register.html",
                error="Username sudah digunakan!"
            )

        # cek email

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )

        if cur.fetchone():

            cur.close()
            conn.close()

            return render_template(
                "register.html",
                error="Email sudah terdaftar!"
            )

        # simpan akun

        cur.execute("""
            INSERT INTO users
            (
                nama,
                email,
                username,
                password,
                role
            )
            VALUES
            (%s,%s,%s,%s,%s)
        """,(
            nama,
            email,
            username,
            password,
            "petugas"
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect("/")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM gardu")
    jumlah_gardu = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT penyulang) FROM gardu")
    jumlah_penyulang = cur.fetchone()[0]

    # beban masih banyak yang NULL (belum ada data pengukuran asli)
    cur.execute("SELECT COUNT(*) FROM gardu WHERE beban > 100")
    overload = cur.fetchone()[0]

    cur.execute("SELECT AVG(beban) FROM gardu WHERE beban IS NOT NULL")
    avg_result = cur.fetchone()[0]
    rata_beban = round(avg_result) if avg_result is not None else 0

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        gardu=jumlah_gardu,
        penyulang=jumlah_penyulang,
        overload=overload,
        beban=rata_beban
    )

@app.route("/gardu")
def gardu():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    cari = request.args.get("cari", "").strip()
    tahun = request.args.get("tahun", "").strip()
    triwulan = request.args.get("triwulan", "").strip()

    tahun_awal = 2026
    tahun_sekarang = datetime.now().year

    daftar_tahun = [
        str(t)
        for t in range(tahun_awal, tahun_sekarang + 1)
    ]

    if tahun == "":
        tahun = str(tahun_sekarang)

    daftar_triwulan = [
        "Triwulan 1",
        "Triwulan 2",
        "Triwulan 3",
        "Triwulan 4"
    ]

    if triwulan == "":
        triwulan = "Triwulan 1"

    sql = """

        SELECT

            no_urut,
            nama_gardu,
            penyulang,
            no_gardu,
            wilayah_kerja,
            jenis,
            daya_kva_pln,
            tahun,
            triwulan

        FROM gardu

        WHERE 1=1

    """

    params = []

    if tahun != "":
        sql += " AND tahun=%s"
        params.append(tahun)

    if triwulan != "":
        sql += " AND triwulan=%s"
        params.append(triwulan)

    if cari != "":
        sql += " AND LOWER(nama_gardu) LIKE LOWER(%s)"
        params.append(f"%{cari}%")

    sql += """

        ORDER BY

        no_urut ASC

    """

    cursor.execute(sql, tuple(params))

    rows = cursor.fetchall()

    conn.close()

    data = []

    for row in rows:

        data.append({

            "nomor": row[0],
            "nama": row[1],
            "penyulang": row[2],
            "nogardu": row[3],
            "wilayah": row[4],
            "jenis": row[5],
            "daya": row[6],
            "tahun": row[7],
            "triwulan": row[8]

        })

    return render_template(

        "gardu.html",

        username=session["username"],

        data=data,

        cari=cari,

        tahun=tahun,

        triwulan=triwulan,

        daftar_tahun=daftar_tahun,

        daftar_triwulan=daftar_triwulan

    )

@app.route("/download_gardu")
def download_gardu():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()

    tahun = request.args.get("tahun", "")
    triwulan = request.args.get("triwulan", "")
    cari = request.args.get("cari", "")

    sql = """

        SELECT
            no_urut AS "No",
            nama_gardu AS "Nama Gardu",
            penyulang AS "Penyulang",
            no_gardu AS "No Gardu",
            wilayah_kerja AS "Wilayah",
            jenis AS "Jenis",
            daya_kva_pln AS "Daya (kVA)",
            tahun AS "Tahun",
            triwulan AS "Triwulan"
        FROM gardu
        WHERE 1=1
    """

    params = []

    if tahun != "":
        sql += " AND tahun = %s"
        params.append(tahun)

    if triwulan != "":
        sql += " AND triwulan = %s"
        params.append(triwulan)

    if cari != "":
        sql += " AND LOWER(nama_gardu) LIKE LOWER(%s)"
        params.append(f"%{cari}%")

    sql += " ORDER BY no_urut"

    df = pd.read_sql_query(
        sql,
        conn,
        params=tuple(params)
    )

    conn.close()

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Data Gardu"
        )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="Data_Gardu.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/edit_gardu/<int:no_urut>", methods=["GET", "POST"])
def edit_gardu(no_urut):

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("""
            UPDATE gardu
            SET
                nama_gardu=%s,
                penyulang=%s,
                no_gardu=%s,
                wilayah_kerja=%s,
                jenis=%s,
                daya_kva_pln=%s,
                tahun=%s,
                triwulan=%s
            WHERE no_urut=%s
        """, (

            request.form["nama_gardu"],
            request.form["penyulang"],
            request.form["no_gardu"],
            request.form["wilayah"],
            request.form["jenis"],
            request.form["daya"],
            request.form["tahun"],
            request.form["triwulan"],
            no_urut

        ))

        conn.commit()
        conn.close()

        return redirect("/gardu")

    cursor.execute("""

        SELECT
            no_urut,
            nama_gardu,
            penyulang,
            no_gardu,
            wilayah_kerja,
            jenis,
            daya_kva_pln,
            tahun,
            triwulan
        FROM gardu
        WHERE no_urut=%s
    """, (no_urut,))

    row = cursor.fetchone()

    cursor.execute("""
        SELECT DISTINCT tahun
        FROM gardu
        WHERE tahun IS NOT NULL
        ORDER BY tahun DESC
    """)

    daftar_tahun = [
        str(x[0])
        for x in cursor.fetchall()
    ]

    if len(daftar_tahun) == 0:
        daftar_tahun = ["2026"]

    daftar_triwulan = [
        "Triwulan 1",
        "Triwulan 2",
        "Triwulan 3",
        "Triwulan 4"
    ]

    conn.close()

    gardu = {
        "nomor": row[0],
        "nama": row[1],
        "penyulang": row[2],
        "nogardu": row[3],
        "wilayah": row[4],
        "jenis": row[5],
        "daya": row[6],
        "tahun": str(row[7]),
        "triwulan": row[8]
    }

    return render_template(
        "edit_gardu.html",
        username=session["username"],
        gardu=gardu,
        daftar_tahun=daftar_tahun,
        daftar_triwulan=daftar_triwulan
    )

@app.route("/hapus_gardu/<int:no_urut>")
def hapus_gardu(no_urut):

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM gardu
        WHERE no_urut=%s
    """, (no_urut,))

    conn.commit()
    conn.close()
    return redirect("/gardu")

@app.route("/tambah_gardu", methods=["GET", "POST"])
def tambah_gardu():

    if "username" not in session:
        return redirect("/")

    tahun_awal = 2026
    tahun_sekarang = datetime.now().year

    daftar_tahun = [
        str(t)
        for t in range(tahun_awal, tahun_sekarang + 1)
    ]

    daftar_triwulan = [
        "Triwulan 1",
        "Triwulan 2",
        "Triwulan 3",
        "Triwulan 4"
    ]

    if request.method == "POST":

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO gardu
            (
                no_urut,
                nama_gardu,
                penyulang,
                no_gardu,
                wilayah_kerja,
                jenis,
                daya_kva_pln,
                tahun,
                triwulan
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s,%s)

        """,(

            request.form["nomor"],
            request.form["nama_gardu"],
            request.form["penyulang"],
            request.form["no_gardu"],
            request.form["wilayah"],
            request.form["jenis"],
            request.form["daya"],
            request.form["tahun"],
            request.form["triwulan"]

        ))

        conn.commit()
        conn.close()

        return redirect("/gardu")

    return render_template(
        "tambah_gardu.html",
        username=session["username"],
        daftar_tahun=daftar_tahun,
        daftar_triwulan=daftar_triwulan
    )

@app.route("/penyulang")
def penyulang():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cari = request.args.get("cari", "").strip()
    tahun = request.args.get("tahun", "").strip()
    triwulan = request.args.get("triwulan", "").strip()

    tahun_awal = 2026
    tahun_sekarang = datetime.now().year

    daftar_tahun = [
        str(t)
        for t in range(tahun_awal, tahun_sekarang + 1)
    ]

    if tahun == "":
        tahun = str(tahun_sekarang)

    daftar_triwulan = [
        "Triwulan 1",
        "Triwulan 2",
        "Triwulan 3",
        "Triwulan 4"
    ]

    if triwulan == "":
        triwulan = "Triwulan 1"

    sql = """
        SELECT
            penyulang,
            COUNT(*)
        FROM gardu
        WHERE penyulang IS NOT NULL
        AND penyulang <> ''
    """

    params = []

    if tahun != "":
        sql += " AND tahun=%s"
        params.append(tahun)

    if triwulan != "":
        sql += " AND triwulan=%s"
        params.append(triwulan)

    if cari != "":
        sql += " AND LOWER(penyulang) LIKE LOWER(%s)"
        params.append(f"%{cari}%")

    sql += """
        GROUP BY penyulang
        ORDER BY penyulang
    """

    cur.execute(sql, tuple(params))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "penyulang.html",
        username=session["username"],
        data=data,
        total=len(data),
        cari=cari,
        tahun=tahun,
        triwulan=triwulan,
        daftar_tahun=daftar_tahun,
        daftar_triwulan=daftar_triwulan
    )

@app.route("/pembebanan", methods=["GET", "POST"])
def pembebanan():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    tahun_awal = 2026
    tahun_sekarang = datetime.now().year

    daftar_tahun = [
        str(t)
        for t in range(tahun_awal, tahun_sekarang + 1)
    ]

    daftar_triwulan = [
        "Triwulan 1",
        "Triwulan 2",
        "Triwulan 3",
        "Triwulan 4"
    ]

    tahun = request.values.get(
        "tahun",
        str(tahun_sekarang)
    )

    triwulan = request.values.get(
        "triwulan",
        "Triwulan 1"
    )

    cur.execute("""
        SELECT
            nama_gardu,
            daya_kva_pln
        FROM gardu
        WHERE tahun=%s
        AND triwulan=%s
        ORDER BY nama_gardu
    """, (
        tahun,
        triwulan
    ))

    gardu_list = cur.fetchall()
    gardu_data = {}

    for row in gardu_list:
        gardu_data[row[0]] = row[1]

    print(gardu_list)
    print(gardu_data)

    hasil = None

    if request.method == "POST":
        print("===== POST MASUK =====")
        print(request.form)

        nama_gardu = request.form["nama_gardu"]
        kva = float(request.form["kva"])
        rn = float(request.form["rn"])
        sn = float(request.form["sn"])
        tn = float(request.form["tn"])

        total_r = sum(
            float(request.form[f"r{i}"])
            for i in range(1, 9)
        )

        total_s = sum(
            float(request.form[f"s{i}"])
            for i in range(1, 9)
        )

        total_t = sum(
            float(request.form[f"t{i}"])
            for i in range(1, 9)
        )

        tegangan = (
            rn +

            sn +

            tn
        ) / 3

        arus_nominal = (
            kva * 1000
        ) / (
            1.732 * tegangan
        )

        arus_rata = (
            total_r +
            total_s +
            total_t
        ) / 3

        persen = (
            arus_rata /
            arus_nominal
        ) * 100

        if persen < 80:
            status = "Normal"

        elif persen < 100:
            status = "Waspada"

        else:
            status = "Overload"

        print("Nama Gardu :", nama_gardu)
        print("KVA :", kva)
        print("R :", total_r)
        print("S :", total_s)
        print("T :", total_t)
        print("Persen :", persen)
        print("Status :", status)

        cur.execute("""
            INSERT INTO riwayat_pembebanan
            (
                nama_gardu,
                total_r,
                total_s,
                total_t,
                arus_nominal,
                arus_rata,
                beban,
                status
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)

        """, (

            nama_gardu,
            round(total_r, 2),
            round(total_s, 2),
            round(total_t, 2),
            round(arus_nominal, 2),
            round(arus_rata, 2),
            round(persen, 2),
            status
        ))

        conn.commit()

        print("INSERT BERHASIL")

        hasil = {

            "total_r": round(total_r, 2),
            "total_s": round(total_s, 2),
            "total_t": round(total_t, 2),
            "nominal": round(arus_nominal, 2),
            "rata": round(arus_rata, 2),
            "persen": round(persen, 2),
            "status": status
        }

    cur.close()
    conn.close()

    return render_template(
        "pembebanan.html",
        gardu_list=gardu_list,
        gardu_data=gardu_data,
        hasil=hasil,
        tahun=tahun,
        triwulan=triwulan,
        daftar_tahun=daftar_tahun,
        daftar_triwulan=daftar_triwulan,
        username=session["username"]
    )

@app.route("/pengecekan", methods=["GET", "POST"])
def pengecekan():

    if "username" not in session:
        return redirect("/")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (nama_gardu)
            nama_gardu,
            beban,
            status
        FROM riwayat_pembebanan
        ORDER BY nama_gardu, id DESC
    """)

    rows = cur.fetchall()

    print("ROWS =", rows)

    gardu_data = {}

    for row in rows:
        gardu_data[row[0]] = {
            "beban": row[1],
            "status": row[2]
        }

    print("GARDU_DATA =", gardu_data)

    sekarang = datetime.now()

    tanggal = int(
        request.args.get(
            "tanggal",
            sekarang.day
        )
    )

    bulan = int(
        request.args.get(
            "bulan",
            sekarang.month
        )
    )

    tahun = int(
        request.args.get(
            "tahun",
            sekarang.year
        )
    )

    tahun_list = list(
        range(
            2026,
            sekarang.year + 1
        )
    )

    if request.method == "POST":

        nama_gardu = request.form["nama_gardu"]
        petugas = request.form["petugas"]
        keterangan = request.form["keterangan"]
        tegangan = "tegangan" in request.form
        arus = "arus" in request.form
        overload = "overload" in request.form
        suhu = "suhu" in request.form

        tanggal_cek = date(
            tahun,
            bulan,
            tanggal
        )

        cur.execute("""
            INSERT INTO pengecekan
            (
                nama_gardu,
                petugas,
                tanggal,
                tegangan,
                arus,
                overload,
                suhu,
                keterangan
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (

            nama_gardu,
            petugas,
            tanggal_cek,
            tegangan,
            arus,
            overload,
            suhu,
            keterangan
        ))

        conn.commit()

    tanggal_filter = date(
        tahun,
        bulan,
        tanggal
    )

    cur.execute("""
        SELECT
            p.nama_gardu,
            r.beban,
            r.status,
            p.petugas,
            p.tegangan,
            p.arus,
            p.overload,
            p.suhu,
            p.keterangan
        FROM pengecekan p
        LEFT JOIN (
            SELECT DISTINCT ON (nama_gardu)
                nama_gardu,
                beban,
                status
            FROM riwayat_pembebanan
            ORDER BY nama_gardu, id DESC
        ) r
        ON p.nama_gardu = r.nama_gardu
        WHERE p.tanggal = %s
        ORDER BY p.id DESC
    """, (tanggal_filter,))

    hasil_cek = []

    for row in cur.fetchall():

        status = (
            row[2]
            or row[3]
            or row[4]
            or row[5]
        )

        hasil_cek.append({
            "gardu": row[0],
            "beban": row[1],
            "status_pembebanan": row[2],
            "petugas": row[3],
            "tegangan": row[4],
            "arus": row[5],
            "overload": row[6],
            "suhu": row[7],
            "keterangan": row[8],
            "status":
                "Sudah Dicek"
                if (row[4] or row[5] or row[6] or row[7])
                else "Belum Dicek"

        })

    cur.close()
    conn.close()

    return render_template(

        "pengecekan.html",
        username=session["username"],
        gardu_data=gardu_data,
        hasil_cek=hasil_cek,
        tanggal=tanggal,
        bulan=bulan,
        tahun=tahun,
        tahun_list=tahun_list
    )

    if request.method == "POST":

        print("===== POST MASUK =====")
        print(request.form)

        nama_gardu = request.form["nama_gardu"]

        kva = float(request.form["kva"])

        rn = float(request.form["rn"])
        sn = float(request.form["sn"])
        tn = float(request.form["tn"])

        total_r = sum(
            float(request.form[f"r{i}"])
            for i in range(1, 9)
        )

        total_s = sum(
            float(request.form[f"s{i}"])
            for i in range(1, 9)
        )

        total_t = sum(
            float(request.form[f"t{i}"])
            for i in range(1, 9)
        )

        tegangan = (
            rn +
            sn +
            tn
        ) / 3

        arus_nominal = (
            kva * 1000
        ) / (
            1.732 * tegangan

        )

        arus_rata = (
            total_r +
            total_s +
            total_t
        ) / 3

        persen = (
            arus_rata /
            arus_nominal
        ) * 100

        if persen < 80:
            status = "Normal"

        elif persen < 100:
            status = "Waspada"

        else:
            status = "Overload"

        cur.execute("""
            INSERT INTO riwayat_pembebanan
            (
                nama_gardu,
                total_r,
                total_s,
                total_t,
                arus_nominal,
                arus_rata,
                beban,
                status
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)

        """, (
            nama_gardu,
            round(total_r, 2),
            round(total_s, 2),
            round(total_t, 2),
            round(arus_nominal, 2),
            round(arus_rata, 2),
            round(persen, 2),
            status
        ))

        conn.commit()
        hasil = {

            "total_r": round(total_r, 2),
            "total_s": round(total_s, 2),
            "total_t": round(total_t, 2),
            "nominal": round(arus_nominal, 2),
            "rata": round(arus_rata, 2),
            "persen": round(persen, 2),
            "status": status
        }

        cur.close()
        conn.close()

    return render_template(

        "pembebanan.html",
        gardu_list=gardu_list,
        gardu_data=gardu_data,
        hasil=hasil,
        username=session["username"],
        tahun=tahun,
        triwulan=triwulan,
        daftar_tahun=daftar_tahun,
        daftar_triwulan=daftar_triwulan
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)