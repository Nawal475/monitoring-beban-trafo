from flask import Flask, render_template, request, redirect, session
import psycopg2

app = Flask(__name__)
app.secret_key = "pln123"


# KONEKSI NEON
def get_connection():
    return psycopg2.connect(
        host="ep-shiny-morning-aok0mute-pooler.c-2.ap-southeast-1.aws.neon.tech",
        database="neondb",
        user="neondb_owner",
        password="npg_EIlvTr5z2BZX",
        sslmode="require"
    )


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if request.method == "POST":
        session["username"] = request.form["username"]

    username = session.get("username", "Admin")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM gardu")
    jumlah_gardu = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT penyulang) FROM gardu")
    jumlah_penyulang = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM gardu WHERE beban > 100")
    overload = cur.fetchone()[0]

    cur.execute("SELECT AVG(beban) FROM gardu")
    rata_beban = round(cur.fetchone()[0])

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        gardu=jumlah_gardu,
        penyulang=jumlah_penyulang,
        overload=overload,
        beban=rata_beban
    )


@app.route("/gardu")
def gardu():

    penyulang = request.args.get("penyulang")

    conn = get_connection()
    cur = conn.cursor()

    if penyulang:
        cur.execute("""
            SELECT nama,
                   penyulang,
                   kapasitas,
                   arus,
                   beban,
                   status
            FROM gardu
            WHERE penyulang=%s
        """, (penyulang,))
    else:
        cur.execute("""
            SELECT nama,
                   penyulang,
                   kapasitas,
                   arus,
                   beban,
                   status
            FROM gardu
        """)

    rows = cur.fetchall()

    data = []

    for row in rows:
        data.append({
            "nama": row[0],
            "penyulang": row[1],
            "kapasitas": row[2],
            "arus": row[3],
            "beban": row[4],
            "status": row[5]
        })

    cur.close()
    conn.close()

    username = session.get("username", "Admin")

    return render_template(
        "gardu.html",
        data=data,
        username=username
    )


@app.route("/penyulang")
def penyulang():

    username = session.get("username", "Admin")

    return render_template(
        "penyulang.html",
        username=username
    )


@app.route("/pembebanan")
def pembebanan():

    username = session.get("username", "Admin")

    return render_template(
        "pembebanan.html",
        username=username
    )


@app.route("/pengecekan")
def pengecekan():

    username = session.get("username", "Admin")

    return render_template(
        "pengecekan.html",
        username=username
    )


if __name__ == "__main__":
    app.run(debug=True)