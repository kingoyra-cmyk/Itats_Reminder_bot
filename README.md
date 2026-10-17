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
- `/hubungkan` — Panduan menghubungkan akun ITATS pribadi (khusus teman beda prodi/kelas)
- `/pause` — Menjeda notifikasi berkala
- `/resume` — Mengaktifkan kembali notifikasi
- `/logout` — Berhenti berlangganan notifikasi

---

## 💡 Panduan Hubungkan Akun Pribadi (Beda Prodi / Kelas)

### 🤔 Siapa yang Membutuhkan Fitur Ini?
- **Teman Sekelas (Informatika):** **TIDAK PERLU** hubungkan akun. Cukup klik **/start** di bot Telegram, kamu sudah otomatis menerima broadcast pengingat tugas dan presensi kelas tanpa ribet.
- **Teman Beda Prodi / Beda Kelas / Beda Semester:** Karena jadwal kuliah dan tugasnya berbeda, teman beda prodi dapat menghubungkan akun Classroom ITATS masing-masing agar bot memantau akun pribadi mereka secara independen.

---

### 🚀 Cara 1: Login Otomatis 1-Klik (via `login_teman.bat` — Paling Mudah Tanpa F12)
Jika temanmu tidak punya laptop atau merasa ribet menyalin kode cURL:
1. Minta temanmu menekan **/start** di bot Telegram **[@ItatsReminder_Bot](https://t.me/ItatsReminder_Bot)**.
2. Di laptop host (Aryo), double-click file **`login_teman.bat`**.
3. Di layar terminal, pilih nomor temanmu dari daftar pelanggan yang muncul.
4. Jendela login ITATS akan otomatis terbuka di browser. Temanmu tinggal mengetikkan NPM & Password miliknya (atau dibantu ketikkan).
5. Begitu berhasil login, jendela akan otomatis tertutup sendiri.
6. Sesi cookie langsung tersimpan ke database dan bot **otomatis mengirim pesan konfirmasi sukses ke Telegram HP temanmu!**

---

### 💻 Cara 2: Lewat Browser Laptop / PC (Copy cURL — Mandiri)
1. Buka browser (Chrome / Edge / Firefox) di laptop/PC dan pastikan sudah login ke [classroom.itats.ac.id/mahasiswa/home](https://classroom.itats.ac.id/mahasiswa/home).
2. Tekan tombol **F12** di keyboard (atau klik kanan di mana saja ➡️ pilih **Inspect**).
3. Klik tab **Network** pada panel inspect yang muncul.
4. Muat ulang halaman dengan menekan **F5** (Refresh).
5. Pada kolom pencarian atau daftar nama request, cari dan klik kanan pada request bernama **`home`**.
6. Pilih **Copy** ➡️ **Copy as cURL** *(bisa pilih `Copy as cURL (bash)` atau `Copy as cURL (cmd)`)*.
7. Buka chat bot Telegram **[@ItatsReminder_Bot](https://t.me/ItatsReminder_Bot)**, lalu **Paste (tempelkan)** teks panjang cURL tersebut langsung ke chat bot dan kirim!
8. Bot akan otomatis mengekstrak cookie sesi, memverifikasinya, dan mengaktifkan pemantauan khusus untuk akunmu.


---

### 📱 Cara 3: Jika Menggunakan HP / Smartphone (Tanpa Laptop)
Jika temanmu hanya punya HP dan tidak ada laptop:
1. **Opsi Paling Cepat:** Temanmu minta tolong ke kamu (Aryo) untuk menjalankan **`login_teman.bat`** (Cara 1 di atas). Temanmu hanya perlu kirim /start di Telegram.
2. **Opsi Mandiri via HP Android:**
   - Install **Kiwi Browser** dari Google Play Store (browser ini memiliki fitur Developer Tools F12 bawaan).
   - Login ke `classroom.itats.ac.id`, buka menu titik tiga (⋮) ➡️ **Developer Tools** ➡️ tab **Network** ➡️ Refresh.
   - Salin cURL request `home`, lalu kirimkan langsung ke chat bot Telegram **[@ItatsReminder_Bot](https://t.me/ItatsReminder_Bot)**.

---

### 🔒 Keamanan & Privasi
- Bot **TIDAK PERNAH** meminta atau menyimpan password ITATS kamu.
- Bot hanya menggunakan cookie sesi sementara untuk membaca API tugas belum selesai dan jadwal presensi kuliah hari ini.
- Kamu bisa memutus sambungan kapan saja dengan mengetik **/logout** di chat bot.

