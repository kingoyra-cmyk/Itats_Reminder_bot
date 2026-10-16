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

# Cache pengingat presensi agar tidak spam dalam 1 hari
# Key: f"{chat_id}_{mata_kuliah}"
notified_presensi = set()

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

def handle_start(chat_id: int, user_name: str, username: str):
    user = database.get_user(chat_id)
    if user and user.get("session_cookie"):
        text = (
            f"👋 *Halo, {user_name}!* Selamat datang kembali di *Bot Pengingat ITATS*.\n\n"
            f"Akun Classroom ITATS kamu saat ini: *Terhubung & Aktif* ✅\n\n"
            f"📌 *Menu Cepat:*\n"
            f"• /cek - Cek tugas & presensi kamu sekarang\n"
            f"• /status - Lihat status akun & pemantau\n"
            f"• /hubungkan - Perbarui sesi / cookie Classroom\n"
            f"• /pause - Jeda pengingat otomatis\n"
            f"• /resume - Lanjutkan pengingat otomatis\n"
            f"• /logout - Hapus data akun kamu dari bot"
        )
    else:
        text = (
            f"👋 *Halo, {user_name}!* Selamat datang di *Bot Pengingat Classroom ITATS*.\n\n"
            f"Bot ini bisa otomatis memantau:\n"
            f"• 📚 *Tugas kuliah yang belum selesai*\n"
            f"• 📝 *Presensi kuliah yang dibuka & belum kamu hadiri*\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Akun kamu belum terhubung!*\n"
            f"Ketik **/hubungkan** untuk panduan cara menghubungkan akun Classroom ITATS kamu ke bot ini."
        )
    send_message(chat_id, text)

def handle_hubungkan(chat_id: int):
    text = (
        f"🔑 *CARA MENGHUBUNGKAN AKUN CLASSROOM ITATS*\n\n"
        f"1. Buka browser tempat kamu login di [classroom.itats.ac.id](https://classroom.itats.ac.id/mahasiswa/home).\n"
        f"2. Tekan tombol **F12** di keyboard $\\rightarrow$ buka tab **Network**.\n"
        f"3. **Refresh halaman** browser kamu (`Ctrl + R` atau `F5`).\n"
        f"4. Di daftar request yang muncul, klik kanan pada baris paling atas (**`home`**).\n"
        f"5. Pilih **Copy** $\\rightarrow$ **Copy as cURL** (POSIX atau Windows).\n"
        f"6. **Paste (tempel) hasil copy cURL tersebut langsung ke chat bot ini!**\n\n"
        f"💡 _Bot akan otomatis mengekstrak cookie sesi kamu, mengujinya, dan langsung mengaktifkan pengingat untuk akunmu!_"
    )
    send_message(chat_id, text)

def handle_curl_message(chat_id: int, user_name: str, username: str, text: str):
    send_message(chat_id, "⏳ *Sedang memverifikasi sesi Classroom kamu...* Mohon tunggu sebentar.")
    
    parsed = itats_service.parse_curl_command(text)
    if not parsed["session"]:
        send_message(chat_id, "❌ *Gagal:* Cookie `classroom_itats_session` tidak ditemukan di dalam teks yang kamu kirim. Pastikan kamu menyalin perintah cURL dari request `home` di tab Network.")
        return

    # Uji koneksi ke ITATS
    count, new_session, new_xsrf, is_expired = itats_service.check_tasks(
        parsed["session"],
        parsed["xsrf"],
        parsed["cf_clearance"],
        parsed["user_agent"]
    )

    if is_expired or count is None:
        send_message(
            chat_id,
            "❌ *Gagal Terhubung!* Sesi Classroom kamu tampaknya sudah kedaluwarsa atau tidak valid.\n"
            "Pastikan kamu sedang dalam kondisi login di browser saat menyalin cURL, lalu coba kirimkan lagi."
        )
        return

    # Simpan ke Database
    active_session = new_session if new_session else parsed["session"]
    active_xsrf = new_xsrf if new_xsrf else parsed["xsrf"]
    database.save_or_update_user(
        chat_id=chat_id,
        name=user_name,
        username=username or "",
        session=active_session,
        xsrf=active_xsrf,
        cf_clearance=parsed["cf_clearance"],
        user_agent=parsed["user_agent"]
    )
    database.update_last_task_count(chat_id, count)

    sukses_text = (
        f"🎉 *SELAMAT, AKUN BERHASIL TERHUBUNG!*\n\n"
        f"👤 Nama: *{user_name}*\n"
        f"📚 Tugas Belum Selesai Saat Ini: *{count} tugas*\n"
        f"⏱️ Interval Pemantauan: *Setiap {CHECK_INTERVAL_MINUTES} menit*\n\n"
        f"Bot sekarang otomatis mengawasi tugas dan presensi kuliahmu. Kamu bisa ketik **/cek** kapan saja!"
    )
    send_message(chat_id, sukses_text)

def handle_cek(chat_id: int):
    user = database.get_user(chat_id)
    if not user or not user.get("session_cookie"):
        send_message(chat_id, "⚠️ Akun kamu belum terhubung ke bot ini. Ketik **/hubungkan** untuk menghubungkan akun.")
        return

    send_message(chat_id, "🔍 *Sedang memeriksa data terbaru di Classroom ITATS...*")

    # 1. Cek Tugas
    count, new_sess, new_xsrf, is_expired = itats_service.check_tasks(
        user["session_cookie"],
        user.get("xsrf_token", ""),
        user.get("cf_clearance", ""),
        user.get("user_agent", "")
    )

    if is_expired:
        send_message(
            chat_id,
            "⚠️ *Sesi Classroom Kamu Telah Kedaluwarsa!*\n"
            "Silakan perbarui sesi kamu dengan mengirimkan cURL baru. Ketik **/hubungkan** untuk panduannya."
        )
        return

    # Auto keep-alive update
    if new_sess:
        database.update_user_cookies(chat_id, new_sess, new_xsrf)

    # 2. Cek Presensi
    presensi_list, p_expired = itats_service.check_presensi(
        new_sess or user["session_cookie"],
        new_xsrf or user.get("xsrf_token", ""),
        user.get("cf_clearance", ""),
        user.get("user_agent", "")
    )

    waktu_str = datetime.now().strftime("%H:%M:%S WIB")
    
    # Format Laporan Tugas
    if count == 0:
        tugas_str = "0 tugas (Semua beres! 🎉)"
    else:
        tugas_str = f"*{count} tugas* yang belum selesai! ⚠️"

    # Format Laporan Presensi
    if not presensi_list:
        presensi_str = "• Tidak ada presensi yang sedang dibuka hari ini."
    else:
        p_lines = []
        for p in presensi_list:
            icon = "✅" if p["sudah_hadir"] else "🔴 *BELUM ABSEN*"
            status_txt = "Sudah Hadir" if p["sudah_hadir"] else "Belum Hadir"
            p_lines.append(f"• *{p['mata_kuliah']}*: {icon} ({status_txt}) - Batas: `{p['batas']}`")
        presensi_str = "\n".join(p_lines)

    hasil_text = (
        f"📋 *STATUS CLASSROOM ITATS KAMU*\n"
        f"⏰ _Dicek pada: {waktu_str}_\n\n"
        f"📚 *Status Tugas:*\n"
        f"{tugas_str}\n\n"
        f"📝 *Presensi Dibuka Hari Ini:*\n"
        f"{presensi_str}\n\n"
        f"🔗 [Buka Classroom ITATS](https://classroom.itats.ac.id/mahasiswa/home)"
    )
    send_message(chat_id, hasil_text)

def handle_status(chat_id: int):
    user = database.get_user(chat_id)
    if not user or not user.get("session_cookie"):
        send_message(chat_id, "⚠️ Akun kamu belum terhubung. Ketik **/hubungkan** untuk menghubungkan akun.")
        return

    status_aktif = "🟢 Aktif Memantau" if user.get("is_active") else "🟡 Dijeda (Paused)"
    text = (
        f"⚙️ *STATUS AKUN BOT KAMU*\n\n"
        f"👤 Nama: *{user.get('name', '-')}*\n"
        f"🆔 Chat ID: `{chat_id}`\n"
        f"📡 Status Pemantau: *{status_aktif}*\n"
        f"⏱️ Interval Pengecekan: *Setiap {CHECK_INTERVAL_MINUTES} menit*\n"
        f"📅 Terakhir Diperbarui: `{user.get('updated_at', '-')}`\n\n"
        f"Gunakan **/pause** untuk jeda atau **/resume** untuk mengaktifkan kembali."
    )
    send_message(chat_id, text)

def handle_pause(chat_id: int):
    database.set_user_status(chat_id, False)
    send_message(chat_id, "⏸️ *Pengingat Otomatis Dijeda.*\nBot tidak akan mengirimkan notifikasi berkala. Ketik **/resume** jika ingin mengaktifkannya kembali.")

def handle_resume(chat_id: int):
    database.set_user_status(chat_id, True)
    send_message(chat_id, "▶️ *Pengingat Otomatis Diaktifkan Kembali!*\nBot akan kembali memantau tugas dan presensi kamu secara berkala.")

def handle_logout(chat_id: int):
    database.delete_user(chat_id)
    send_message(chat_id, "👋 *Akun Kamu Berhasil Dihapus!*\nData sesi kamu telah dihapus dari bot ini. Jika ingin menggunakan bot lagi di kemudian hari, cukup ketik **/hubungkan**.")

def background_monitor_loop():
    """
    Loop pemantauan di latar belakang:
    Mengecek semua user yang terdaftar di database setiap CHECK_INTERVAL_MINUTES menit.
    """
    print("[*] Background monitor loop telah berjalan...")
    while True:
        try:
            active_users = database.get_all_active_users()
            now_str = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{now_str}] Memeriksa {len(active_users)} pengguna terdaftar...")

            for u in active_users:
                cid = u["chat_id"]
                name = u.get("name", str(cid))
                sess = u.get("session_cookie", "")
                xsrf = u.get("xsrf_token", "")
                cf = u.get("cf_clearance", "")
                ua = u.get("user_agent", "")
                last_task = u.get("last_task_count", 0)

                # 1. Pengecekan Tugas
                count, new_sess, new_xsrf, is_expired = itats_service.check_tasks(sess, xsrf, cf, ua)
                if is_expired:
                    print(f"[{now_str}] [!] Sesi user {name} ({cid}) expired.")
                    send_message(
                        cid,
                        "⚠️ *PERINGATAN SESI ITATS:*\n"
                        "Sesi Classroom ITATS kamu telah kedaluwarsa. Bot tidak bisa memantau tugas/presensi kamu lagi.\n"
                        "Silakan perbarui sesi kamu dengan mengetik **/hubungkan**."
                    )
                    database.set_user_status(cid, False)
                    continue

                # Auto Keep-Alive per user
                if new_sess:
                    database.update_user_cookies(cid, new_sess, new_xsrf)
                    sess = new_sess
                    if new_xsrf:
                        xsrf = new_xsrf

                if isinstance(count, int):
                    if count > 0 and count != last_task:
                        pesan = (
                            f"📢 *REMINDER TUGAS ITATS!*\n\n"
                            f"Halo *{name}*, kamu memiliki *{count} tugas* yang belum selesai!\n"
                            f"🔗 Akses langsung: [Classroom ITATS]({itats_service.ENDPOINT_HOME})\n\n"
                            f"⏰ _Dicek pada: {now_str}_"
                        )
                        send_message(cid, pesan)
                        database.update_last_task_count(cid, count)
                    elif count == 0 and last_task > 0:
                        send_message(cid, "🎉 *Hebat!* Semua tugas Classroom kamu sudah selesai dikerjakan.")
                        database.update_last_task_count(cid, 0)

                # 2. Pengecekan Presensi
                presensi_list, p_expired = itats_service.check_presensi(sess, xsrf, cf, ua)
                if presensi_list:
                    for p in presensi_list:
                        mk = p["mata_kuliah"]
                        key = f"{cid}_{mk}"
                        if not p["sudah_hadir"]:
                            if key not in notified_presensi:
                                pesan_absen = (
                                    f"⚠️ *PENGINGAT PRESENSI ITATS!*\n\n"
                                    f"Halo *{name}*, kamu belum presensi untuk:\n"
                                    f"📌 Mata Kuliah: *{mk}*\n"
                                    f"⏰ Batas Waktu: *{p['batas']}*\n\n"
                                    f"👉 Segera buka [Classroom ITATS]({itats_service.ENDPOINT_HOME}) dan lakukan presensi sekarang!"
                                )
                                send_message(cid, pesan_absen)
                                notified_presensi.add(key)
                        else:
                            if key in notified_presensi:
                                notified_presensi.remove(key)

        except Exception as e:
            print(f"[!] Error pada background monitor: {e}")

        time.sleep(CHECK_INTERVAL_MINUTES * 60)

def auto_register_admin():
    """Mendaftarkan akun pemilik dari .env secara otomatis ke database"""
    admin_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    session = os.getenv("CLASSROOM_SESSION", "").strip()
    xsrf = os.getenv("XSRF_TOKEN", "").strip()
    cf = os.getenv("CF_CLEARANCE", "").strip()
    ua = os.getenv("USER_AGENT", "").strip()

    if admin_chat_id and session:
        try:
            cid = int(admin_chat_id)
            existing = database.get_user(cid)
            if not existing:
                database.save_or_update_user(cid, "Aryo (Admin)", "aryosyarif", session, xsrf, cf, ua)
                print(f"[+] Akun utama (Admin Chat ID {cid}) otomatis terdaftar di database.")
        except Exception as e:
            print(f"[!] Gagal auto-register admin: {e}")

def main():
    database.init_db()
    auto_register_admin()

    print("=" * 60)
    print("   🤖 BOT PENGINGAT CLASSROOM ITATS (MULTI-USER ENGINE)   ")
    print("=" * 60)
    print(f"[+] Total pengguna terdaftar di database: {database.get_user_count()}")
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

                    # Routing Perintah
                    if text.startswith("/start"):
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
