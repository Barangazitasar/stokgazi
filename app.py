from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import bcrypt
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["UPLOAD_FOLDER"] = "static/uploads"

# Veritabanı bağlantısı
def get_db_connection():
    conn = sqlite3.connect("veritabani.db")
    conn.row_factory = sqlite3.Row
    return conn

# Giriş Sayfası
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        kullanici = request.form["username"]
        sifre = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (kullanici,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(sifre.encode('utf-8'), user["sifre"].encode('utf-8')):
            session["kullanici"] = kullanici
            session["rol"] = user["rol"]
            return redirect(url_for("dashboard"))
        else:
            return render_template("index.html", hata="Kullanıcı adı veya şifre hatalı.")
    return render_template("index.html")

# Kayıt Sayfası
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi")
        sifre = request.form.get("sifre")

        if not kullanici_adi or not sifre:
            flash("Tüm alanları doldurun.", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
        mevcut = cursor.fetchone()

        if mevcut:
            conn.close()
            flash("Bu kullanıcı adı zaten kayıtlı!", "warning")
            return redirect(url_for("register"))

        hashed = bcrypt.hashpw(sifre.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute("INSERT INTO kullanicilar (kullanici_adi, sifre, rol) VALUES (?, ?, ?)",
                       (kullanici_adi, hashed, "kullanici"))
        conn.commit()
        conn.close()

        flash("Kayıt başarıyla oluşturuldu. Giriş yapabilirsiniz.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS toplam FROM urunler")
    toplam_urun = cursor.fetchone()["toplam"]

    cursor.execute("SELECT SUM(miktar) AS stok FROM urunler")
    toplam_stok = cursor.fetchone()["stok"] or 0

    cursor.execute("SELECT COUNT(*) AS kritik FROM urunler WHERE miktar < 50")
    kritik_urun = cursor.fetchone()["kritik"]

    cursor.execute("SELECT ad, miktar FROM urunler ORDER BY miktar DESC LIMIT 5")
    veriler = cursor.fetchall()
    urun_adlari = [v["ad"] for v in veriler]
    urun_miktarlari = [v["miktar"] for v in veriler]

    cursor.execute("SELECT profil_resmi FROM kullanicilar WHERE kullanici_adi = ?", (session["kullanici"],))
    profil = cursor.fetchone()
    profil_resmi = profil["profil_resmi"] if profil and profil["profil_resmi"] else "default.png"

    conn.close()

    return render_template("dashboard.html",
                           kullanici=session["kullanici"],
                           toplam_urun=toplam_urun,
                           toplam_stok=toplam_stok,
                           kritik_urun=kritik_urun,
                           urun_adlari=urun_adlari,
                           urun_miktarlari=urun_miktarlari,
                           profil_resmi=profil_resmi,
                           rol=session["rol"])

# Çıkış
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Ürünler
@app.route("/urunler", methods=["GET", "POST"])
def urunler():
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        ad = request.form["ad"]
        kategori = request.form["kategori"]
        miktar = request.form["miktar"]
        fiyat = request.form["fiyat"]
        kullanici_adi = session["kullanici"]

        cursor.execute("""
            INSERT INTO urunler (ad, kategori, miktar, fiyat, kullanici_adi)
            VALUES (?, ?, ?, ?, ?)
        """, (ad, kategori, miktar, fiyat, kullanici_adi))
        conn.commit()
        flash("Ürün başarıyla eklendi!")
        conn.close()
        return redirect(url_for("urunler"))

    arama = request.args.get("arama", "")
    if arama:
        cursor.execute("""
            SELECT * FROM urunler
            WHERE ad LIKE ? OR kategori LIKE ?
        """, (f"%{arama}%", f"%{arama}%"))
    else:
        cursor.execute("SELECT * FROM urunler")
    urunler = cursor.fetchall()

    cursor.execute("SELECT ad FROM urunler WHERE miktar < 50")
    kritik_urunler = [row["ad"] for row in cursor.fetchall()]

    conn.close()

    return render_template("urunler.html",
                           urunler=urunler,
                           arama=arama,
                           kritik_urunler=kritik_urunler)

@app.route("/urun_sil/<int:id>", methods=["POST"])
def urun_sil(id):
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM hareketler WHERE urun_id = ?", (id,))
    cursor.execute("DELETE FROM urunler WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Ürün ve bağlı hareketler silindi.", "danger")
    return redirect(url_for("urunler"))

# Hareketler
@app.route("/hareketler", methods=["GET", "POST"])
def hareketler():
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        urun_id = request.form["urun_id"]
        tur = request.form["tur"]
        miktar = int(request.form["miktar"])
        tarih = request.form["tarih"]
        kullanici_adi = session["kullanici"]

        if tur == "giris":
            cursor.execute("UPDATE urunler SET miktar = miktar + ? WHERE id = ?", (miktar, urun_id))
        else:
            cursor.execute("UPDATE urunler SET miktar = miktar - ? WHERE id = ?", (miktar, urun_id))

        cursor.execute("""
            INSERT INTO hareketler (urun_id, tur, miktar, tarih, kullanici_adi)
            VALUES (?, ?, ?, ?, ?)
        """, (urun_id, tur, miktar, tarih, kullanici_adi))
        conn.commit()
        flash("Hareket başarıyla kaydedildi.")
        return redirect(url_for("hareketler"))

    cursor.execute("SELECT id, ad FROM urunler")
    urunler = cursor.fetchall()

    cursor.execute("""
        SELECT h.id, u.ad AS urun_adi, h.tur, h.miktar, h.tarih, h.kullanici_adi
        FROM hareketler h
        JOIN urunler u ON h.urun_id = u.id
        ORDER BY h.tarih DESC
    """)
    hareketler = cursor.fetchall()
    conn.close()

    return render_template("hareketler.html", urunler=urunler, hareketler=hareketler, kullanici=session["kullanici"])

# Grafikler
@app.route("/grafikler")
def grafikler():
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ad, miktar FROM urunler ORDER BY miktar DESC LIMIT 5")
    veriler = cursor.fetchall()
    urun_adlari = [v["ad"] for v in veriler]
    urun_miktarlari = [v["miktar"] for v in veriler]
    conn.close()

    return render_template("grafik.html", urun_adlari=urun_adlari, urun_miktarlari=urun_miktarlari)

# Profil
@app.route("/profil", methods=["GET", "POST"])
def profil():
    if "kullanici" not in session:
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        yeni_ad = request.form["kullanici_adi"]
        yeni_sifre = request.form.get("sifre")
        dosya = request.files.get("profil_resmi")

        if yeni_sifre:
            hashed = bcrypt.hashpw(yeni_sifre.encode(), bcrypt.gensalt()).decode()
            cursor.execute("UPDATE kullanicilar SET sifre = ? WHERE kullanici_adi = ?", (hashed, session["kullanici"]))

        if yeni_ad and yeni_ad != session["kullanici"]:
            cursor.execute("UPDATE kullanicilar SET kullanici_adi = ? WHERE kullanici_adi = ?", (yeni_ad, session["kullanici"]))
            session["kullanici"] = yeni_ad

        if dosya and dosya.filename:
            filename = f"{session['kullanici']}.png"
            yol = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            dosya.save(yol)
            cursor.execute("UPDATE kullanicilar SET profil_resmi = ? WHERE kullanici_adi = ?", (filename, session["kullanici"]))

        conn.commit()
        flash("Profil güncellendi.")
        return redirect(url_for("profil"))

    cursor.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (session["kullanici"],))
    kullanici = cursor.fetchone()
    conn.close()
    return render_template("profil.html", kullanici=kullanici)

# Admin Paneli
@app.route("/admin")
def admin_panel():
    if "kullanici" not in session or session.get("rol") != "admin":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kullanicilar")
    kullanicilar = cursor.fetchall()
    conn.close()

    return render_template("admin.html", kullanici=session["kullanici"], kullanicilar=kullanicilar)

@app.route("/kullanici_sil/<int:id>")
def kullanici_sil(id):
    if "kullanici" not in session or session.get("rol") != "admin":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM kullanicilar WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Kullanıcı başarıyla silindi.")
    return redirect(url_for("admin_panel"))

@app.route("/rol_degistir/<int:id>")
def rol_degistir(id):
    if "kullanici" not in session or session.get("rol") != "admin":
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rol FROM kullanicilar WHERE id = ?", (id,))
    user = cursor.fetchone()

    if user:
        yeni_rol = "admin" if user["rol"] == "kullanici" else "kullanici"
        cursor.execute("UPDATE kullanicilar SET rol = ? WHERE id = ?", (yeni_rol, id))
        conn.commit()

    conn.close()
    flash("Kullanıcının yetkisi güncellendi.")
    return redirect(url_for("admin_panel"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

