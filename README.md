# 🤖 Bot Pengingat Classroom ITATS

Bot cerdas pemantau **Tugas & Presensi Kuliah** di **[Classroom ITATS](https://classroom.itats.ac.id)** secara otomatis, terintegrasi langsung dengan notifikasi interaktif **Telegram**.

---

## ✨ Fitur Utama
- 🔑 **Login Otomatis (Auto-Grab Cookie):** Cukup login normal di jendela browser yang terbuka otomatis, sesi dan cookie langsung tersedot tanpa perlu buka F12 / DevTools sama sekali!
- 👥 **Multi-User Telegram Bot:** Teman sekelas **tidak perlu login / cari cookie**, cukup klik **/start** di bot Telegram untuk otomatis menerima pengingat.
- 🔔 **Pengingat Presensi Otomatis:** Memeriksa mata kuliah yang presensinya dibuka hari ini. Jika belum hadir, bot akan otomatis mengirim peringatan darurat ke Telegram sebelum batas waktu habis.
- 📚 **Pemantau Tugas Belum Selesai:** Mengecek jumlah tugas secara berkala dan memberi tahu jika ada tugas baru.
- 🔄 **Auto Keep-Alive Session:** Memperpanjang sesi login secara otomatis saat pengecekan berjalan sehingga sesi tidak mudah kedaluwarsa.
- 💬 **Perintah Chat Interaktif:** Ketik `/cek` kapan saja di Telegram untuk melihat rekap tugas & jadwal presensi hari ini secara instan.

---

## 📁 Struktur File
- **`bot.py`**: Entry point utama bot pengingat (Multi-User Engine).
- **`auto_login.py`**: Script otomatisasi penyedot cookie dari browser Edge/Chrome.
- **`database.py`**: Manajemen database SQLite untuk data pengguna.
- **`itats_service.py`**: Layanan scraping dan parser Classroom ITATS.
- **`login_otomatis.bat`**: Double-click untuk login dan ambil cookie otomatis.
- **`run.bat`**: Double-click untuk menjalankan bot pemantau di Windows.
- **`test_telegram.bat`**: Double-click untuk tes pengiriman notifikasi ke Telegram.
- **`requirements.txt`**: Daftar dependensi library Python.

---

## ⚙️ Cara Pemasangan & Penggunaan

### 1. Install Dependensi
```bash
pip install -r requirements.txt
```

### 2. Konfigurasi [.env](file:///c:/AntiGravity/itats_reminder/.env)
Salin `.env.example` menjadi `.env`, lalu masukkan token Telegram kamu:
```env
TELEGRAM_BOT_TOKEN=token_bot_kamu
TELEGRAM_CHAT_ID=id_telegram_kamu
```

### 3. Login Classroom Otomatis (Tanpa F12)
Double-click file **`login_otomatis.bat`**:
- Jendela login ITATS akan terbuka otomatis.
- Masukkan NPM & Password kamu.
- Begitu berhasil login, jendela akan otomatis tertutup dan cookie langsung tersimpan ke `.env` serta database!

### 4. Jalankan Bot
Double-click file **`run.bat`** *(atau ketik `python bot.py`)*.

---

## 📱 Perintah Telegram
- `/start` — Mendaftar sebagai penerima pengingat kelas (Otomatis tanpa login)
- `/cek` — Melihat status tugas & presensi kuliah hari ini
- `/status` — Melihat status akun dan koneksi pemantau
- `/hubungkan` — Hubungkan akun ITATS pribadi (khusus untuk teman yang beda prodi)
- `/pause` — Menjeda notifikasi berkala
- `/resume` — Mengaktifkan kembali notifikasi
- `/logout` — Berhenti berlangganan notifikasi
