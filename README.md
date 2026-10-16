# 🤖 Bot Pengingat Classroom ITATS

Bot cerdas pemantau **Tugas & Presensi Kuliah** di **[Classroom ITATS](https://classroom.itats.ac.id)** secara otomatis, terintegrasi langsung dengan notifikasi **Telegram**.

---

## ✨ Fitur Utama
- 🔔 **Pengingat Presensi Otomatis:** Memeriksa mata kuliah yang presensinya dibuka hari ini. Jika belum hadir, bot akan otomatis mengirim peringatan darurat ke Telegram sebelum batas waktu habis.
- 📚 **Pemantau Tugas Belum Selesai:** Mengecek jumlah tugas secara berkala dan memberi tahu jika ada tugas baru.
- 🔄 **Auto Keep-Alive Session:** Memperpanjang sesi login secara otomatis saat pengecekan berjalan sehingga sesi tidak mudah kedaluwarsa.
- 🛡️ **Bypass Cloudflare Turnstile:** Menggunakan engine `curl` bawaan Windows untuk kelancaran akses API ITATS tanpa terblokir proteksi bot.

---

## 📁 Struktur File
- **`bot.py`**: Script utama bot pengingat.
- **`.env.example`**: Template konfigurasi token & cookies.
- **`.env`**: File konfigurasi asli (berisi kredensial rahasia, jangan dibagikan).
- **`run.bat`**: Double-click untuk menjalankan bot pemantau di Windows.
- **`test_telegram.bat`**: Double-click untuk tes pengiriman notifikasi ke Telegram.
- **`requirements.txt`**: Daftar dependensi library Python.

---

## ⚙️ Cara Pemasangan & Konfigurasi

### 1. Install Dependensi
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi [.env](file:///c:/AntiGravity/itats_reminder/.env)
Salin `.env.example` menjadi `.env`, lalu lengkapi isinya:

1. **Token Telegram Bot (`TELEGRAM_BOT_TOKEN`)**: Buat bot baru di **@BotFather** Telegram.
2. **Chat ID Telegram (`TELEGRAM_CHAT_ID`)**: Ambil ID akun kamu dari **@userinfobot**.
3. **Cookie Sesi ITATS (`CLASSROOM_SESSION`, `XSRF_TOKEN`, `CF_CLEARANCE`)**:
   - Buka browser tempat kamu login di `classroom.itats.ac.id/mahasiswa/home`.
   - Tekan `F12` $\rightarrow$ tab **Network** $\rightarrow$ Refresh (`F5`).
   - Klik kanan pada baris request `home` $\rightarrow$ **Copy** $\rightarrow$ **Copy as cURL**.
   - Salin nilai cookie yang sesuai ke file `.env`.

---

## 🚀 Menjalankan Bot
- **Windows:** Double-click file `run.bat`.
- **Terminal:**
  ```bash
  python bot.py
  ```
