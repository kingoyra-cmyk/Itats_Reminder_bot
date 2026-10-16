import os
import sys
import time
from datetime import datetime

# Pastikan console Windows mendukung UTF-8 (emoticon / unicode)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests
from dotenv import load_dotenv

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
CLASSROOM_SESSION = os.getenv("CLASSROOM_SESSION", "").strip()
XSRF_TOKEN = os.getenv("XSRF_TOKEN", "").strip()
CF_CLEARANCE = os.getenv("CF_CLEARANCE", "").strip()
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0").strip()
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "15"))

BASE_URL = "https://classroom.itats.ac.id"
ENDPOINT_TUGAS = f"{BASE_URL}/mahasiswa/getTugasBelumSelesai"

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/mahasiswa/home"
    }

def get_cookies():
    cookies = {}
    if CLASSROOM_SESSION:
        cookies["classroom_itats_session"] = CLASSROOM_SESSION
    if XSRF_TOKEN:
        cookies["XSRF-TOKEN"] = XSRF_TOKEN
    return cookies

def kirim_telegram(pesan: str) -> bool:
    """Mengirim pesan notifikasi ke Telegram user."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] Gagal kirim Telegram: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diisi di .env")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("[+] Notifikasi berhasil terkirim ke Telegram!")
            return True
        else:
            print(f"[!] Respon Telegram ({res.status_code}): {res.text}")
            return False
    except Exception as e:
        print(f"[!] Error saat menghubungi server Telegram: {e}")
        return False

import subprocess
import json

import re

def perbarui_cookie_env(nama_key: str, nilai_baru: str):
    """Menyimpan cookie sesi terbaru ke file .env agar tidak pernah expired"""
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
        except Exception as e:
            print(f"[!] Gagal memperbarui {nama_key} di .env: {e}")

def cek_status_classroom():
    """
    Melakukan request ke endpoint getTugasBelumSelesai via curl.exe
    dan otomatis memperbarui session cookie (Auto Keep-Alive).
    Mengembalikan integer jumlah tugas, atau None jika gagal.
    """
    global CLASSROOM_SESSION, XSRF_TOKEN
    if not CLASSROOM_SESSION:
        print("[!] CLASSROOM_SESSION belum diisi di .env!")
        return None

    try:
        cookie_list = []
        if CLASSROOM_SESSION:
            cookie_list.append(f"classroom_itats_session={CLASSROOM_SESSION}")
        if XSRF_TOKEN:
            cookie_list.append(f"XSRF-TOKEN={XSRF_TOKEN}")
        if CF_CLEARANCE:
            cookie_list.append(f"cf_clearance={CF_CLEARANCE}")
        cookie_str = "; ".join(cookie_list)

        cmd = [
            "curl.exe", "-s", "-i",
            "-H", f"User-Agent: {USER_AGENT}",
            "-H", "x-requested-with: XMLHttpRequest",
            "-H", "Accept: application/json, text/javascript, */*; q=0.01",
            "-H", f"Referer: {BASE_URL}/mahasiswa/home",
            "-b", cookie_str,
            ENDPOINT_TUGAS
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        raw_output = proc.stdout

        # Cek apakah sesi habis (di-redirect ke login)
        if "login" in raw_output or "Redirecting" in raw_output:
            print("[!] Sesi Classroom telah berakhir (Expired). Perlu perbarui cookie!")
            kirim_telegram(
                "⚠️ *PERINGATAN SESI ITATS:*\n"
                "Sesi login Classroom ITATS kamu telah kedaluwarsa.\n"
                "Silakan login ulang di web dan perbarui `CLASSROOM_SESSION` di file `.env`."
            )
            return "EXPIRED"

        # Pisahkan headers dan JSON body
        parts = re.split(r'\r?\n\r?\n', raw_output)
        header_text = parts[0] if len(parts) > 0 else ""
        body_text = parts[-1].strip() if len(parts) > 1 else raw_output.strip()

        # Otomatis tangkap dan perbarui cookie sesi baru (Auto Keep-Alive)
        new_cookies = dict(re.findall(r'Set-Cookie:\s*([^=]+)=([^;]+)', header_text, re.IGNORECASE))
        if "classroom_itats_session" in new_cookies:
            CLASSROOM_SESSION = new_cookies["classroom_itats_session"]
            perbarui_cookie_env("CLASSROOM_SESSION", CLASSROOM_SESSION)
        if "XSRF-TOKEN" in new_cookies:
            XSRF_TOKEN = new_cookies["XSRF-TOKEN"]
            perbarui_cookie_env("XSRF_TOKEN", XSRF_TOKEN)

        data = json.loads(body_text)
        return data.get("count", 0)
    except Exception as e:
        print(f"[!] Error mengambil data dari Classroom: {e}")
        return None

def cek_presensi_classroom():
    """
    Mengecek presensi kuliah yang sedang dibuka di Classroom ITATS.
    Mengembalikan list dict: [{'mata_kuliah': ..., 'sudah_hadir': bool, 'batas': ...}]
    """
    try:
        from bs4 import BeautifulSoup
        cookie_list = []
        if CLASSROOM_SESSION:
            cookie_list.append(f"classroom_itats_session={CLASSROOM_SESSION}")
        if XSRF_TOKEN:
            cookie_list.append(f"XSRF-TOKEN={XSRF_TOKEN}")
        if CF_CLEARANCE:
            cookie_list.append(f"cf_clearance={CF_CLEARANCE}")
        cookie_str = "; ".join(cookie_list)

        cmd = [
            "curl.exe", "-s",
            "-H", f"User-Agent: {USER_AGENT}",
            "-H", f"Referer: {BASE_URL}/login",
            "-b", cookie_str,
            f"{BASE_URL}/mahasiswa/home"
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        html = proc.stdout
        if "login" in html or "Redirecting" in html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        cols = soup.find_all("div", class_="student-activity-column")
        if len(cols) < 2:
            return []

        presensi_col = cols[1]
        cards = presensi_col.find_all("div", class_="activity-item-card")
        hasil = []
        for card in cards:
            text = card.get_text(separator=" ", strip=True)
            h6 = card.find("h6")
            mk = h6.get_text(strip=True) if h6 else "Kuliah"
            sudah_hadir = "Sudah Hadir" in text or "Presensi Tercatat" in text
            batas_match = re.search(r'Batas:\s*([^\(\n]+)', text)
            batas = batas_match.group(1).strip() if batas_match else "Hari ini"

            hasil.append({
                "mata_kuliah": mk,
                "sudah_hadir": sudah_hadir,
                "batas": batas
            })
        return hasil
    except Exception as e:
        print(f"[!] Error saat mengambil data presensi: {e}")
        return []

def main():
    print("=" * 60)
    print("   🤖 BOT PENGINGAT CLASSROOM ITATS (ANTIGRAVITY)   ")
    print("=" * 60)
    
    # Mode test kirim pesan
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("[*] Menguji pengiriman pesan ke Telegram...")
        sukses = kirim_telegram("🎉 *Tes Berhasil!* Bot Pengingat Classroom ITATS terhubung dengan akun Telegram kamu!")
        if sukses:
            print("[+] Tes selesai dengan sukses!")
        else:
            print("[!] Tes gagal, silakan periksa Token Bot dan Chat ID di .env.")
        return

    # Validasi konfigurasi dasar
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[X] Konfigurasi Telegram belum lengkap.")
        print("    Buka file .env dan masukkan TELEGRAM_BOT_TOKEN serta TELEGRAM_CHAT_ID.")
        return

    if not CLASSROOM_SESSION:
        print("[!] Perhatian: CLASSROOM_SESSION di .env belum diisi.")
        print("    Kamu bisa mengambilnya dari DevTools -> Application -> Cookies.")
        print("    Bot tetap akan mencoba kirim notifikasi awal ke Telegram...")

    # Notifikasi awal bot aktif
    waktu_mulai = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    kirim_telegram(
        f"🚀 *Bot Pengingat Classroom ITATS Aktif!*\n"
        f"📅 Waktu Mulai: `{waktu_mulai}`\n"
        f"⏱️ Interval Cek: Setiap {CHECK_INTERVAL_MINUTES} menit\n\n"
        f"Bot akan memantau:\n"
        f"• 📚 Tugas yang belum selesai\n"
        f"• 📝 Presensi yang dibuka & belum dihadiri"
    )

    tugas_sebelumnya = None
    presensi_diingatkan = set()

    while True:
        waktu_cek = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{waktu_cek}] Melakukan pengecekan ke Classroom ITATS...")

        # 1. Cek Tugas Belum Selesai
        hasil = cek_status_classroom()

        if hasil == "EXPIRED":
            print("[*] Menunggu 30 menit sebelum mencoba kembali...")
            time.sleep(1800)
            continue

        if isinstance(hasil, int):
            print(f"[{waktu_cek}] Status Tugas: {hasil} tugas belum selesai.")

            # Kirim notifikasi jika ada tugas dan jumlahnya berubah
            if hasil > 0 and hasil != tugas_sebelumnya:
                pesan = (
                    f"📢 *REMINDER TUGAS ITATS!*\n\n"
                    f"📌 Kamu memiliki *{hasil} tugas* yang belum selesai!\n"
                    f"🔗 Akses langsung: [Classroom ITATS]({BASE_URL}/mahasiswa/home)\n\n"
                    f"⏰ _Dicek pada: {waktu_cek}_"
                )
                kirim_telegram(pesan)
                tugas_sebelumnya = hasil
            elif hasil == 0:
                if tugas_sebelumnya is not None and tugas_sebelumnya > 0:
                    kirim_telegram("🎉 *Hebat!* Semua tugas Classroom kamu sudah selesai dikerjakan.")
                tugas_sebelumnya = 0

        # 2. Cek Presensi yang Sedang Dibuka
        daftar_presensi = cek_presensi_classroom()
        if daftar_presensi is not None:
            for item in daftar_presensi:
                mk = item["mata_kuliah"]
                if not item["sudah_hadir"]:
                    print(f"[{waktu_cek}] ⚠️ Presensi BELUM HADIR: {mk} (Batas: {item['batas']})")
                    if mk not in presensi_diingatkan:
                        pesan_absen = (
                            f"⚠️ *PENGINGAT PRESENSI ITATS!*\n\n"
                            f"Kamu belum melakukan presensi untuk:\n"
                            f"📌 Mata Kuliah: *{mk}*\n"
                            f"⏰ Batas Waktu: *{item['batas']}*\n\n"
                            f"👉 Segera buka [Classroom ITATS]({BASE_URL}/mahasiswa/home) dan lakukan presensi sekarang!"
                        )
                        kirim_telegram(pesan_absen)
                        presensi_diingatkan.add(mk)
                else:
                    print(f"[{waktu_cek}] ✅ Presensi SUDAH HADIR: {mk}")
                    if mk in presensi_diingatkan:
                        presensi_diingatkan.remove(mk)

        # Tunggu interval berikutnya
        print(f"[*] Menunggu {CHECK_INTERVAL_MINUTES} menit untuk pengecekan berikutnya...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
