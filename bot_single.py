# ==============================================================
# BOT PENGINGAT CLASSROOM ITATS (MODE STANDALONE / PRIBADI)
# ==============================================================
# Mode ini menggunakan data langsung dari file .env untuk 1 pengguna.
# ==============================================================

import os
import sys
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
CLASSROOM_SESSION = os.getenv("CLASSROOM_SESSION", "").strip()
XSRF_TOKEN = os.getenv("XSRF_TOKEN", "").strip()
CF_CLEARANCE = os.getenv("CF_CLEARANCE", "").strip()
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0").strip()
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))

import itats_service

def kirim_telegram(pesan: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def perbarui_cookie_env(nama_key: str, nilai_baru: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(env_path, "w", encoding="utf-8") as f:
                found = False
                for line in lines:
                    if line.startswith(f"{nama_key}="):
                        f.write(f"{nama_key}={nilai_baru}\n")
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f"{nama_key}={nilai_baru}\n")
        except Exception:
            pass

def main():
    global CLASSROOM_SESSION, XSRF_TOKEN
    print("=" * 60)
    print("   🤖 BOT PENGINGAT CLASSROOM ITATS (MODE STANDALONE)   ")
    print("=" * 60)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not CLASSROOM_SESSION:
        print("[!] Konfigurasi di .env belum lengkap. Silakan lengkapi file .env terlebih dahulu.")
        return

    kirim_telegram(
        f"🚀 *Bot Pengingat Classroom ITATS Aktif!*\n"
        f"📅 Waktu Mulai: `{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}`\n"
        f"⏱️ Interval: Setiap {CHECK_INTERVAL_MINUTES} menit\n\n"
        f"Bot memantau:\n• 📚 Tugas Belum Selesai\n• 📝 Presensi Kuliah"
    )

    tugas_sebelumnya = None
    presensi_diingatkan = set()

    while True:
        waktu_cek = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{waktu_cek}] Melakukan pengecekan...")

        # 1. Cek Tugas
        count, new_sess, new_xsrf, is_expired = itats_service.check_tasks(CLASSROOM_SESSION, XSRF_TOKEN, CF_CLEARANCE, USER_AGENT)
        if is_expired:
            print("[!] Sesi Classroom telah kedaluwarsa.")
            kirim_telegram("⚠️ *Sesi Classroom Kedaluwarsa!* Silakan login ulang dan perbarui file .env.")
            time.sleep(1800)
            continue

        if new_sess:
            CLASSROOM_SESSION = new_sess
            perbarui_cookie_env("CLASSROOM_SESSION", CLASSROOM_SESSION)
        if new_xsrf:
            XSRF_TOKEN = new_xsrf
            perbarui_cookie_env("XSRF_TOKEN", XSRF_TOKEN)

        if isinstance(count, int):
            print(f"[{waktu_cek}] Status Tugas: {count} tugas.")
            if count > 0 and count != tugas_sebelumnya:
                pesan = (
                    f"📢 *REMINDER TUGAS ITATS!*\n\n"
                    f"📌 Kamu memiliki *{count} tugas* yang belum selesai!\n"
                    f"🔗 [Buka Classroom ITATS]({itats_service.ENDPOINT_HOME})"
                )
                kirim_telegram(pesan)
                tugas_sebelumnya = count
            elif count == 0 and tugas_sebelumnya is not None and tugas_sebelumnya > 0:
                kirim_telegram("🎉 *Semua tugas Classroom kamu sudah selesai!*")
                tugas_sebelumnya = 0

        # 2. Cek Presensi
        presensi_list, p_expired = itats_service.check_presensi(CLASSROOM_SESSION, XSRF_TOKEN, CF_CLEARANCE, USER_AGENT)
        if presensi_list:
            for p in presensi_list:
                mk = p["mata_kuliah"]
                if not p["sudah_hadir"]:
                    print(f"[{waktu_cek}] ⚠️ Presensi BELUM HADIR: {mk}")
                    if mk not in presensi_diingatkan:
                        kirim_telegram(
                            f"⚠️ *PENGINGAT PRESENSI ITATS!*\n\n"
                            f"Kamu belum melakukan presensi untuk:\n"
                            f"📌 Mata Kuliah: *{mk}*\n"
                            f"⏰ Batas Waktu: *{p['batas']}*\n\n"
                            f"👉 [Buka Classroom ITATS]({itats_service.ENDPOINT_HOME})"
                        )
                        presensi_diingatkan.add(mk)
                else:
                    print(f"[{waktu_cek}] ✅ Presensi SUDAH HADIR: {mk}")
                    if mk in presensi_diingatkan:
                        presensi_diingatkan.remove(mk)

        print(f"[*] Menunggu {CHECK_INTERVAL_MINUTES} menit...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
