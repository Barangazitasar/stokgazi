import sqlite3
import bcrypt

# Veritabanı bağlantısı
conn = sqlite3.connect("veritabani.db")
cursor = conn.cursor()

# Kullanıcı bilgileri
kullanici_adi = "baran"
sifre = "baran"
rol = "admin"

# Şifreyi hashle
hashed = bcrypt.hashpw(sifre.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# Varsa silip yeniden ekle (isteğe bağlı güvenlik önlemi)
cursor.execute("DELETE FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))

# Kullanıcıyı ekle
cursor.execute("""
INSERT INTO kullanicilar (kullanici_adi, sifre, rol, profil_resmi)
VALUES (?, ?, ?, ?)
""", (kullanici_adi, hashed, rol, "default.png"))

conn.commit()
conn.close()

print("✅ Admin kullanıcısı başarıyla eklendi: baran / baran")
