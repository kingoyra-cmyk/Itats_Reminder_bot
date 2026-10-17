import os
import sys
import time
import threading
from datetime import datetime
import requests
from dotenv import load_dotenv

import database
import itats_service

# UTF-8 support on Windows CMD
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environment
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))

if not TELEGRAM_BOT_TOKEN:
    print("[X] ERROR: TELEGRAM_BOT_TOKEN belum diatur di .env!")
    sys.exit(1)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
ADMIN_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0").strip() or "0")

# Cache pengingat presensi agar tidak spam dalam 1 hari
notified_presensi = set()
last_known_task_count = None

def is_super_admin(chat_id: int) -> bool:
    """Super Admin: hanya pemilik bot berdasarkan .env (full access)"""
    return chat_id == ADMIN_CHAT_ID

def is_admin(chat_id: int) -> bool:
    """Admin: Super Admin ATAU co-admin yang dipromote via /promote"""
    if chat_id == ADMIN_CHAT_ID:
        return True
    user = database.get_user(chat_id)
    return user is not None and user.get("role") in ("admin", "co-admin")

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown", disable_preview: bool = True) -> bool:
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[!] Error kirim pesan ke {chat_id}: {e}")
        return False

def broadcast_message(text: str):
    """Mengirim pesan notifikasi ke semua teman yang terdaftar"""
    subscribers = database.get_all_subscribers()
    for sub in subscribers:
        send_message(sub["chat_id"], text)

def handle_start(chat_id: int, user_name: str, username: str):
    # Daftarkan teman langsung sebagai subscriber (Auto 0-Login!)
    database.register_subscriber(chat_id, user_name, username)

    text = (
        f"🎉 *Halo, {user_name}!* Selamat datang di *Bot Pengingat ITATS*.\n\n"
        f"✅ *Kamu sudah otomatis terhubung ke sistem pengingat kelas!*\n"
        f"Kamu **TIDAK PERLU LOGIN** dan **TIDAK PERLU CARI COOKIE** apa pun. Bot ini sudah otomatis memantau Classroom ITATS dan akan mengirim notifikasi ke chat kamu jika:\n"
        f"• 🔔 *Ada presensi kuliah yang dibuka* (agar tidak kelewat batas absen!)\n"
        f"• 📚 *Ada tugas kuliah baru yang belum selesai*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Perintah yang bisa kamu pakai:*\n"
        f"• /cek - Cek tugas & presensi kuliah hari ini\n"
        f"• /status - Cek status langganan notifikasi kamu\n"
        f"• /pause - Jeda pengingat otomatis sementara\n"
        f"• /resume - Lanjutkan kembali pengingat otomatis\n"
        f"• /hubungkan - *(Opsional)* Hubungkan akun ITATS pribadi jika kamu dari kelas/jurusan lain\n"
        f"• /logout - Berhenti berlangganan dari bot ini"
    )
    send_message(chat_id, text)

def handle_hubungkan(chat_id: int):
    text = (
        f"💡 *PANDUAN HUBUNGKAN AKUN PRIBADI*\n\n"
        f"📌 *Siapa yang perlu hubungkan akun?*\n"
        f"• *Teman Sekelas (Informatika):* **TIDAK PERLU**. Cukup ketik /start kamu sudah otomatis menerima pengingat presensi & tugas kelas.\n"
        f"• *Teman Beda Prodi / Beda Kelas:* Silakan hubungkan akun agar bot memantau mata kuliah pribadimu sendiri.\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💻 *Cara Hubungkan (Lewat Browser Laptop/PC):*\n"
        f"1. Buka [Classroom ITATS](https://classroom.itats.ac.id/mahasiswa/home) di browser (Chrome/Edge/Firefox).\n"
        f"2. Tekan tombol *F12* di keyboard (atau klik kanan ➡️ *Inspect*).\n"
        f"3. Klik tab *Network*, lalu muat ulang halaman (*F5*).\n"
        f"4. Cari request bernama *`home`*, klik kanan ➡️ pilih *Copy* ➡️ *Copy as cURL*.\n"
        f"5. *Paste / tempelkan* teks cURL tersebut langsung ke chat bot ini!\n\n"
        f"📱 *Bagaimana jika lewat HP?*\n"
        f"Cukup buka laptop sekali saja untuk salin cURL di atas, lalu kirimkan teks cURL-nya ke chat bot ini. Setelah terhubung, kamu bisa memantau semuanya langsung lewat HP tanpa perlu buka laptop lagi!\n\n"
        f"🔒 *Catatan Keamanan:* Bot tidak menyimpan password ITATS kamu, hanya membaca cookie sesi sementara untuk jadwal presensi & tugas."
    )
    send_message(chat_id, text)

def handle_curl_message(chat_id: int, user_name: str, username: str, text: str):
    send_message(chat_id, "⏳ *Sedang memverifikasi sesi Classroom pribadi kamu...* Mohon tunggu sebentar.")
    
    parsed = itats_service.parse_curl_command(text)
    if not parsed["session"]:
        send_message(chat_id, "❌ *Gagal:* Cookie sesi tidak ditemukan di dalam teks yang kamu kirim. Pastikan kamu menyalin perintah cURL dari request `home` di tab Network.")
        return

    count, new_session, new_xsrf, is_expired = itats_service.check_tasks(
        parsed["session"],
        parsed["xsrf"],
        parsed["cf_clearance"],
        parsed["user_agent"]
    )

    if is_expired or count is None:
        send_message(
            chat_id,
            "❌ *Gagal Terhubung!* Sesi Classroom tampaknya sudah kedaluwarsa atau tidak valid.\n"
            "Pastikan kamu sedang dalam kondisi login di browser saat menyalin cURL, lalu coba kirimkan lagi."
        )
        return

    active_session = new_session if new_session else parsed["session"]
    active_xsrf = new_xsrf if new_xsrf else parsed["xsrf"]
    database.save_or_update_user(
        chat_id=chat_id,
        name=user_name,
        username=username or "",
        session=active_session,
        xsrf=active_xsrf,
        cf_clearance=parsed["cf_clearance"],
        user_agent=parsed["user_agent"],
        role="custom"
    )
    database.update_last_task_count(chat_id, count)

    sukses_text = (
        f"🎉 *AKUN PRIBADI BERHASIL TERHUBUNG!*\n\n"
        f"👤 Nama: *{user_name}*\n"
        f"📚 Tugas Belum Selesai Saat Ini: *{count} tugas*\n"
        f"⏱️ Interval Pemantauan: *Setiap {CHECK_INTERVAL_MINUTES} menit*\n\n"
        f"Bot sekarang otomatis mengawasi akun pribadimu. Ketik **/cek** kapan saja untuk cek status!"
    )
    send_message(chat_id, sukses_text)

def handle_cek(chat_id: int):
    user = database.get_user(chat_id)
    admin = database.get_admin_user()

    # Tentukan cookie sesi mana yang dipakai: sesi pribadi jika ada, atau sesi kelas utama
    target = user if (user and user.get("session_cookie")) else admin

    if not target or not target.get("session_cookie"):
        send_message(chat_id, "⚠️ Server pemantau sedang offline. Silakan hubungi admin bot.")
        return

    send_message(chat_id, "🔍 *Sedang memeriksa data terbaru di Classroom ITATS...*")

    # 1. Cek Tugas
    count, new_sess, new_xsrf, is_expired = itats_service.check_tasks(
        target["session_cookie"],
        target.get("xsrf_token", ""),
        target.get("cf_clearance", ""),
        target.get("user_agent", "")
    )

    if is_expired:
        send_message(chat_id, "⚠️ Sesi pemantau Classroom kedaluwarsa. Admin perlu memperbarui sesi.")
        return

    if new_sess:
        database.update_user_cookies(target["chat_id"], new_sess, new_xsrf)

    # 2. Cek Presensi
    presensi_list, p_expired = itats_service.check_presensi(
        new_sess or target["session_cookie"],
        new_xsrf or target.get("xsrf_token", ""),
        target.get("cf_clearance", ""),
        target.get("user_agent", "")
    )

    waktu_str = datetime.now().strftime("%H:%M:%S WIB")
    
    # Format Tugas
    if count == 0:
        tugas_str = "0 tugas (Semua beres! 🎉)"
    else:
        tugas_str = f"*{count} tugas* yang belum selesai! ⚠️"

    # Format Presensi
    if not presensi_list:
        presensi_str = "• Tidak ada presensi yang sedang dibuka hari ini."
    else:
        p_lines = []
        for p in presensi_list:
            icon = "✅" if p["sudah_hadir"] else "🔔 *PRESENSI DIBUKA*"
            p_lines.append(f"• *{p['mata_kuliah']}*: {icon}\n  ⏰ Batas: `{p['batas']}`")
        presensi_str = "\n".join(p_lines)

    hasil_text = (
        f"📋 *STATUS CLASSROOM ITATS HARI INI*\n"
        f"⏰ _Dicek pada: {waktu_str}_\n\n"
        f"📚 *Status Tugas:*\n"
        f"{tugas_str}\n\n"
        f"📝 *Presensi Dibuka:*\n"
        f"{presensi_str}\n\n"
        f"🔗 [Buka Classroom ITATS](https://classroom.itats.ac.id/mahasiswa/home)"
    )
    send_message(chat_id, hasil_text)

def handle_status(chat_id: int):
    user = database.get_user(chat_id)
    if not user:
        send_message(chat_id, "⚠️ Kamu belum terdaftar. Ketik **/start** untuk mulai.")
        return

    status_aktif = "🟢 Aktif Menerima Notifikasi" if user.get("is_active") else "🟡 Dijeda (Paused)"
    
    role = user.get("role", "subscriber")
    if role == "admin":
        role_info = "👑 Admin Pemantau Kelas"
    elif role == "custom" or (role != "admin" and user.get("session_cookie")):
        role_info = "🔗 Akun Pribadi (Beda Prodi)"
    else:
        role_info = "👥 Subscriber Kelas (Tanpa Login)"

    text = (
        f"⚙️ *STATUS LANGGANAN KAMU*\n\n"
        f"👤 Nama: *{user.get('name', '-')}*\n"
        f"🆔 Chat ID: `{chat_id}`\n"
        f"📋 Mode: *{role_info}*\n"
        f"📡 Status: *{status_aktif}*\n"
        f"⏱️ Interval Pengecekan: *Setiap {CHECK_INTERVAL_MINUTES} menit*\n\n"
        f"• Ketik **/pause** untuk jeda notifikasi\n"
        f"• Ketik **/resume** untuk mengaktifkan kembali"
    )
    send_message(chat_id, text)

def handle_pause(chat_id: int):
    database.set_user_status(chat_id, False)
    send_message(chat_id, "⏸️ *Notifikasi Pengingat Dijeda.*\nKamu tidak akan menerima pesan berkala. Ketik **/resume** jika ingin mengaktifkan kembali.")

def handle_resume(chat_id: int):
    database.set_user_status(chat_id, True)
    send_message(chat_id, "▶️ *Notifikasi Pengingat Diaktifkan Kembali!*\nKamu akan otomatis menerima pesan pengingat presensi dan tugas.")

def handle_logout(chat_id: int):
    database.delete_user(chat_id)
    send_message(chat_id, "👋 *Kamu Berhasil Berhenti Berlangganan.*\nJika ingin mengaktifkan notifikasi kembali sewaktu-waktu, cukup ketik **/start** kapan saja!")

# ─────────────────────────────────────────────
#   PANEL ADMIN (Hanya bisa diakses oleh Admin)
# ─────────────────────────────────────────────

def handle_admin_panel(chat_id: int):
    """Menampilkan daftar perintah eksklusif admin"""
    is_super = is_super_admin(chat_id)
    text = (
        f"👑 *PANEL ADMIN — BOT PENGINGAT ITATS*\n\n"
        f"📋 *Data & Monitoring:*\n"
        f"• /daftar — Lihat semua pengguna terdaftar\n"
        f"• /sesi — Cek status sesi Classroom aktif\n\n"
        f"📣 *Komunikasi:*\n"
        f"• /broadcast `<pesan>` — Kirim pesan ke semua subscriber\n\n"
        f"🚫 *Manajemen Pengguna:*\n"
        f"• /kick `<chat_id>` — Hapus pengguna dari bot\n"
        f"• /promote `<chat_id>` — Jadikan pengguna sebagai Co-Admin\n"
        f"• /demote `<chat_id>` — Turunkan Co-Admin kembali ke subscriber\n\n"
        f"⚙️ *Sistem:*\n"
        f"• /admin — Tampilkan panel ini\n"
    )
    if not is_super:
        text += "\n_ℹ️ Kamu adalah Co-Admin. Perintah /broadcast, /kick, /promote, /demote hanya bisa dipakai oleh Super Admin._"
    send_message(chat_id, text)

def handle_admin_daftar(chat_id: int):
    """Menampilkan daftar semua pengguna terdaftar"""
    users = database.get_all_subscribers()
    if not users:
        send_message(chat_id, "📭 Belum ada pengguna terdaftar.")
        return

    lines = [f"📋 *DAFTAR PENGGUNA TERDAFTAR ({len(users)} orang)*\n"]
    for i, u in enumerate(users, 1):
        role = u.get("role", "subscriber")
        if role == "admin":
            icon = "👑"
            mode = "Admin"
        elif u.get("session_cookie"):
            icon = "🔗"
            mode = "Akun Pribadi"
        else:
            icon = "👥"
            mode = "Subscriber"
        status = "🟢" if u.get("is_active") else "🔴"
        uname = f"@{u['username']}" if u.get("username") else "tanpa username"
        lines.append(f"{i}. {icon} *{u.get('name', '-')}* ({uname})\n   {status} {mode} | ID: `{u['chat_id']}`")

    send_message(chat_id, "\n".join(lines))

def handle_admin_broadcast(chat_id: int, pesan: str):
    """Broadcast pesan custom ke semua subscriber"""
    if not pesan.strip():
        send_message(chat_id, "⚠️ Format salah. Gunakan: /broadcast pesan kamu di sini")
        return

    subscribers = database.get_all_subscribers()
    sukses = 0
    gagal = 0
    pesan_kirim = f"📢 *PENGUMUMAN DARI ADMIN BOT*\n\n{pesan}"

    for sub in subscribers:
        if sub["chat_id"] == chat_id:
            continue  # Jangan kirim ke diri sendiri
        ok = send_message(sub["chat_id"], pesan_kirim)
        if ok:
            sukses += 1
        else:
            gagal += 1

    send_message(
        chat_id,
        f"✅ *Broadcast Selesai!*\n\n"
        f"📨 Terkirim ke: *{sukses} pengguna*\n"
        f"❌ Gagal: *{gagal} pengguna*\n\n"
        f"_Pesan yang dikirim:_\n\"{pesan}\""
    )

def handle_admin_kick(chat_id: int, target_id_str: str):
    """Hapus pengguna dari bot berdasarkan chat_id"""
    if not target_id_str.strip().isdigit():
        send_message(chat_id, "⚠️ Format salah. Gunakan: /kick 123456789")
        return

    target_id = int(target_id_str.strip())
    if target_id == ADMIN_CHAT_ID:
        send_message(chat_id, "❌ Tidak bisa menghapus akun admin sendiri!")
        return

    user = database.get_user(target_id)
    if not user:
        send_message(chat_id, f"⚠️ Pengguna dengan ID `{target_id}` tidak ditemukan.")
        return

    nama = user.get("name", str(target_id))
    database.delete_user(target_id)
    send_message(target_id, "ℹ️ Kamu telah dihapus dari daftar penerima notifikasi bot oleh admin. Ketik /start jika ingin mendaftar kembali.")
    send_message(chat_id, f"✅ Pengguna *{nama}* (ID: `{target_id}`) berhasil dihapus dari bot.")

def handle_admin_sesi(chat_id: int):
    """Menampilkan status sesi Classroom aktif"""
    admin = database.get_admin_user()
    if not admin or not admin.get("session_cookie"):
        send_message(
            chat_id,
            "❌ *Tidak ada sesi Classroom aktif!*\n"
            "Jalankan `login_otomatis.bat` untuk memperbarui sesi."
        )
        return

    custom_users = database.get_all_active_users_with_cookie()
    non_admin = [u for u in custom_users if u["chat_id"] != admin["chat_id"]]

    updated = admin.get("updated_at", "-")
    text = (
        f"🔑 *STATUS SESI CLASSROOM AKTIF*\n\n"
        f"👑 *Admin (Sesi Utama):*\n"
        f"   Nama: *{admin.get('name', '-')}*\n"
        f"   Terakhir diperbarui: `{updated}`\n\n"
    )
    if non_admin:
        text += f"🔗 *Akun Pribadi Terhubung ({len(non_admin)} akun):*\n"
        for u in non_admin:
            text += f"   • *{u.get('name', '-')}* | Diperbarui: `{u.get('updated_at', '-')}`\n"
    else:
        text += "🔗 *Akun Pribadi:* Belum ada yang terhubung."

    send_message(chat_id, text)

def handle_admin_promote(chat_id: int, target_id_str: str):
    """Promote pengguna menjadi co-admin (hanya super admin)"""
    if not target_id_str.strip().isdigit():
        send_message(chat_id, "⚠️ Format salah. Gunakan: /promote 123456789")
        return
    target_id = int(target_id_str.strip())
    if target_id == ADMIN_CHAT_ID:
        send_message(chat_id, "ℹ️ Kamu sudah menjadi Super Admin, tidak perlu di-promote.")
        return
    user = database.get_user(target_id)
    if not user:
        send_message(chat_id, f"⚠️ Pengguna dengan ID `{target_id}` tidak ditemukan di database.\nPastikan mereka sudah menekan /start terlebih dahulu.")
        return
    nama = user.get("name", str(target_id))
    database.set_user_role(target_id, "co-admin")
    send_message(target_id, f"🎖️ *Selamat, {nama}!*\nKamu telah dipromote menjadi *Co-Admin* bot oleh admin.\nKamu sekarang bisa menggunakan perintah /daftar dan /sesi.")
    send_message(chat_id, f"✅ *{nama}* (ID: `{target_id}`) berhasil dipromote menjadi *Co-Admin*.")

def handle_admin_demote(chat_id: int, target_id_str: str):
    """Turunkan co-admin kembali ke subscriber (hanya super admin)"""
    if not target_id_str.strip().isdigit():
        send_message(chat_id, "⚠️ Format salah. Gunakan: /demote 123456789")
        return
    target_id = int(target_id_str.strip())
    if target_id == ADMIN_CHAT_ID:
        send_message(chat_id, "❌ Tidak bisa menurunkan akun Super Admin sendiri!")
        return
    user = database.get_user(target_id)
    if not user:
        send_message(chat_id, f"⚠️ Pengguna dengan ID `{target_id}` tidak ditemukan.")
        return
    nama = user.get("name", str(target_id))
    # Tentukan role yang sesuai setelah demote
    new_role = "custom" if user.get("session_cookie") else "subscriber"
    database.set_user_role(target_id, new_role)
    send_message(target_id, f"ℹ️ *{nama}*, akses Co-Admin kamu telah dicabut oleh admin.")
    send_message(chat_id, f"✅ *{nama}* (ID: `{target_id}`) berhasil diturunkan kembali ke *{new_role}*.")

def background_monitor_loop():
    """
    Loop pemantauan di latar belakang:
    Mengecek tugas & presensi secara berkala dan membroadcast ke semua teman yang terdaftar.
    """
    global last_known_task_count
    print("[*] Background monitor loop telah berjalan...")
    while True:
        try:
            admin = database.get_admin_user()
            if not admin:
                print("[!] Belum ada sesi pemantau utama di database. Menunggu...")
                time.sleep(60)
                continue

            now_str = datetime.now().strftime("%H:%M:%S")
            subscribers = database.get_all_subscribers()
            print(f"\n[{now_str}] Memeriksa ITATS untuk {len(subscribers)} penerima notifikasi...")

            sess = admin.get("session_cookie", "")
            xsrf = admin.get("xsrf_token", "")
            cf = admin.get("cf_clearance", "")
            ua = admin.get("user_agent", "")

            # 1. Pengecekan Tugas
            count, new_sess, new_xsrf, is_expired = itats_service.check_tasks(sess, xsrf, cf, ua)
            if is_expired:
                print(f"[{now_str}] [!] Sesi pemantau utama EXPIRED!")
                send_message(admin["chat_id"], "⚠️ *Sesi Pemantau Utama Kedaluwarsa!* Mohon perbarui cURL kamu.")
                time.sleep(1800)
                continue

            # Auto Keep-Alive sesi admin
            if new_sess:
                database.update_user_cookies(admin["chat_id"], new_sess, new_xsrf)
                sess = new_sess
                if new_xsrf:
                    xsrf = new_xsrf

            # Notifikasi Tugas jika ada tugas baru
            if isinstance(count, int):
                print(f"[{now_str}] Status Tugas: {count} tugas.")
                if count > 0 and (last_known_task_count is None or count > last_known_task_count):
                    pesan_tugas = (
                        f"📢 *PERINGATAN TUGAS ITATS!*\n\n"
                        f"📌 Ada *{count} tugas* yang belum selesai!\n"
                        f"🔗 [Buka Classroom ITATS]({itats_service.ENDPOINT_HOME})\n\n"
                        f"⏰ _Pengecekan: {now_str}_"
                    )
                    broadcast_message(pesan_tugas)
                    last_known_task_count = count
                elif count == 0 and last_known_task_count is not None and last_known_task_count > 0:
                    broadcast_message("🎉 *Hebat!* Semua tugas Classroom kelas sudah selesai dikerjakan.")
                    last_known_task_count = 0

            # 2. Pengecekan Presensi Dibuka (Kelas Utama)
            presensi_list, p_expired = itats_service.check_presensi(sess, xsrf, cf, ua)
            if presensi_list:
                for p in presensi_list:
                    mk = p["mata_kuliah"]
                    key = f"broadcast_{mk}_{p['batas']}"
                    # Kirim broadcast pengingat presensi jika dibuka dan belum pernah diingatkan hari ini
                    if key not in notified_presensi:
                        pesan_absen = (
                            f"🔔 *PENGINGAT PRESENSI KULIAH ITATS!*\n\n"
                            f"Presensi sedang dibuka untuk:\n"
                            f"📌 Mata Kuliah: *{mk}*\n"
                            f"⏰ Batas Waktu: *{p['batas']}*\n\n"
                            f"👉 Jangan sampai lupa absen! Segera buka [Classroom ITATS]({itats_service.ENDPOINT_HOME}) sekarang!"
                        )
                        broadcast_message(pesan_absen)
                        notified_presensi.add(key)
                        print(f"[{now_str}] [!] Presensi broadcast terkirim: {mk} (Batas: {p['batas']})")

            # 3. Pengecekan Khusus untuk Teman Beda Prodi (Akun Pribadi Custom)
            custom_users = database.get_all_active_users_with_cookie()
            for cu in custom_users:
                if cu["chat_id"] == admin["chat_id"]:
                    continue  # Admin sudah dicek di atas

                c_cid = cu["chat_id"]
                c_name = cu.get("name", "Teman")
                c_sess = cu.get("session_cookie", "")
                c_xsrf = cu.get("xsrf_token", "")
                c_cf = cu.get("cf_clearance", "")
                c_ua = cu.get("user_agent", "")
                c_last_task = cu.get("last_task_count", 0)

                # Cek Tugas Beda Prodi
                c_count, c_newsess, c_newxsrf, c_expired = itats_service.check_tasks(c_sess, c_xsrf, c_cf, c_ua)
                if c_expired:
                    send_message(c_cid, "⚠️ *Sesi Akun ITATS Kamu Kedaluwarsa!*\nKetik /hubungkan untuk memperbarui sesi.")
                    continue

                if c_newsess:
                    database.update_user_cookies(c_cid, c_newsess, c_newxsrf)
                    c_sess = c_newsess

                if isinstance(c_count, int):
                    if c_count > 0 and (c_last_task is None or c_count > c_last_task):
                        send_message(c_cid, f"📢 *PENGINGAT TUGAS ITATS!*\n\nHalo *{c_name}*, ada *{c_count} tugas* belum selesai di akunmu!\n🔗 [Buka Classroom ITATS]({itats_service.ENDPOINT_HOME})")
                        database.update_last_task_count(c_cid, c_count)

                # Cek Presensi Beda Prodi
                c_presensi, _ = itats_service.check_presensi(c_sess, c_xsrf, c_cf, c_ua)
                if c_presensi:
                    for cp in c_presensi:
                        mk = cp["mata_kuliah"]
                        key = f"custom_{c_cid}_{mk}_{cp['batas']}"
                        if not cp["sudah_hadir"] and key not in notified_presensi:
                            send_message(c_cid, f"🔔 *PENGINGAT PRESENSI ITATS!*\n\nHalo *{c_name}*, presensi dibuka untuk:\n📌 Mata Kuliah: *{mk}*\n⏰ Batas Waktu: *{cp['batas']}*\n👉 Segera buka [Classroom ITATS]({itats_service.ENDPOINT_HOME})!")
                            notified_presensi.add(key)

        except Exception as e:
            print(f"[!] Error pada background monitor: {e}")

        time.sleep(CHECK_INTERVAL_MINUTES * 60)

def auto_register_admin():
    """Mendaftarkan akun pemilik dari .env secara otomatis sebagai Admin Pemantau"""
    admin_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    session = os.getenv("CLASSROOM_SESSION", "").strip()
    xsrf = os.getenv("XSRF_TOKEN", "").strip()
    cf = os.getenv("CF_CLEARANCE", "").strip()
    ua = os.getenv("USER_AGENT", "").strip()

    if admin_chat_id and session:
        try:
            cid = int(admin_chat_id)
            database.save_or_update_user(cid, "Aryo (Admin)", "aryosyarif", session, xsrf, cf, ua, role="admin")
            print(f"[+] Akun utama (Admin Chat ID {cid}) siap sebagai pemantau kelas.")
        except Exception as e:
            print(f"[!] Gagal auto-register admin: {e}")

def main():
    database.init_db()
    auto_register_admin()

    print("=" * 60)
    print("   🤖 BOT PENGINGAT CLASSROOM ITATS (MULTI-USER ENGINE)   ")
    print("=" * 60)
    print(f"[+] Total penerima terdaftar: {database.get_user_count()}")
    print("[+] Mode polling Telegram aktif. Mendengarkan pesan masuk...")

    # Jalankan Background Monitoring Thread
    monitor_thread = threading.Thread(target=background_monitor_loop, daemon=True)
    monitor_thread.start()

    # Long Polling Telegram Updates
    offset = None
    while True:
        try:
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            res = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params=params, timeout=25)
            if res.status_code == 200:
                data = res.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg or not msg.get("text"):
                        continue

                    chat_id = msg["chat"]["id"]
                    first_name = msg["from"].get("first_name", "Teman")
                    username = msg["from"].get("username", "")
                    text = msg["text"].strip()

                    # ── Perintah Admin Eksklusif ──
                    if text.startswith("/admin") and is_admin(chat_id):
                        handle_admin_panel(chat_id)
                    elif text.startswith("/daftar") and is_admin(chat_id):
                        handle_admin_daftar(chat_id)
                    elif text.startswith("/sesi") and is_admin(chat_id):
                        handle_admin_sesi(chat_id)
                    elif text.startswith("/broadcast") and is_super_admin(chat_id):
                        pesan = text[len("/broadcast"):].strip()
                        handle_admin_broadcast(chat_id, pesan)
                    elif text.startswith("/kick") and is_super_admin(chat_id):
                        target = text[len("/kick"):].strip()
                        handle_admin_kick(chat_id, target)
                    elif text.startswith("/promote") and is_super_admin(chat_id):
                        target = text[len("/promote"):].strip()
                        handle_admin_promote(chat_id, target)
                    elif text.startswith("/demote") and is_super_admin(chat_id):
                        target = text[len("/demote"):].strip()
                        handle_admin_demote(chat_id, target)
                    # ── Perintah Admin yang diketik orang biasa → tolak diam-diam ──
                    elif text.startswith(("/admin", "/daftar", "/broadcast", "/kick", "/sesi", "/promote", "/demote")) and not is_admin(chat_id):
                        send_message(chat_id, "❓ Perintah tidak dikenali.\nKetik **/cek** untuk cek status tugas & presensi, atau **/help** untuk bantuan.")
                    # ── Perintah Umum ──
                    elif text.startswith("/start"):
                        handle_start(chat_id, first_name, username)
                    elif text.startswith("/hubungkan"):
                        handle_hubungkan(chat_id)
                    elif text.startswith("/cek") or text.startswith("/tugas") or text.startswith("/presensi"):
                        handle_cek(chat_id)
                    elif text.startswith("/status"):
                        handle_status(chat_id)
                    elif text.startswith("/pause"):
                        handle_pause(chat_id)
                    elif text.startswith("/resume"):
                        handle_resume(chat_id)
                    elif text.startswith("/logout"):
                        handle_logout(chat_id)
                    elif text.startswith("/help"):
                        handle_start(chat_id, first_name, username)
                    elif "classroom_itats_session" in text or text.lower().startswith("curl"):
                        handle_curl_message(chat_id, first_name, username, text)
                    else:
                        send_message(
                            chat_id,
                            f"❓ Perintah tidak dikenali.\n"
                            f"Ketik **/cek** untuk cek status tugas & presensi, atau **/help** untuk bantuan."
                        )
            elif res.status_code == 409:
                print("[!] Conflict: Ada instance bot lain yang sedang berjalan. Menunggu 5 detik...")
                time.sleep(5)
        except requests.exceptions.RequestException:
            time.sleep(3)
        except Exception as e:
            print(f"[!] Error di main loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
