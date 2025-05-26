# init_db.py
import sqlite3

# Veritabanı dosyasını oluştur
conn = sqlite3.connect("veritabani.db")
cursor = conn.cursor()

# Kullanıcılar tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS kullanicilar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT UNIQUE NOT NULL,
    sifre TEXT NOT NULL,
    rol TEXT DEFAULT 'kullanici',
    profil_resmi TEXT DEFAULT 'default.png'
)
""")

# Ürünler tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS urunler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL,
    kategori TEXT,
    miktar INTEGER,
    fiyat REAL,
    kullanici_adi TEXT
)
""")

# Hareketler tablosu
cursor.execute("""
CREATE TABLE IF NOT EXISTS hareketler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    urun_id INTEGER,
    tur TEXT,
    miktar INTEGER,
    tarih TEXT,
    kullanici_adi TEXT,
    FOREIGN KEY (urun_id) REFERENCES urunler(id)
)
""")

conn.commit()
conn.close()

print("✅ veritabani.db oluşturuldu ve tablolar kuruldu.")
