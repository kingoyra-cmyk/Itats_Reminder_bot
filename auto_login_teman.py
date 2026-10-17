import subprocess
import json
import time
import os
import shutil
import urllib.request
import requests
import websocket
from dotenv import load_dotenv

import database
import itats_service

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

def send_telegram_msg(chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[!] Gagal mengirim notifikasi Telegram ke {chat_id}: {e}")

def get_target_friend():
    database.init_db()
    subscribers = database.get_all_subscribers()
    
    # Filter teman (selain admin sendiri)
    admin = database.get_admin_user()
    admin_id = admin["chat_id"] if admin else None

    friends = [s for s in subscribers if s["chat_id"] != admin_id]

    print("=" * 65)
    print("   👥 LOGIN OTOMATIS AKUN TEMAN (BEDA PRODI / BEDA KELAS)   ")
    print("=" * 65)

    if friends:
        print("Pilih teman yang ingin dihubungkan akun Classroom ITATS-nya:\n")
        for idx, f in enumerate(friends, 1):
            uname = f"@{f['username']}" if f.get('username') else "Tanpa username"
            status = "Sudah punya akun pribadi" if f.get("session_cookie") else "Subscriber kelas"
            print(f" [{idx}] {f.get('name', 'Teman')} ({uname}) - Chat ID: {f['chat_id']} [{status}]")
        print(f" [{len(friends) + 1}] Input Chat ID / Username teman baru secara manual")
        print(" [0] Batal")
        print("-" * 65)

        while True:
            choice = input(f"Pilih nomor (1-{len(friends) + 1}, atau 0 untuk batal): ").strip()
            if choice == "0":
                return None
            if choice.isdigit():
                c_int = int(choice)
                if 1 <= c_int <= len(friends):
                    target = friends[c_int - 1]
                    return target["chat_id"], target.get("name", "Teman"), target.get("username", "")
                elif c_int == len(friends) + 1:
                    break
            print("Pilihan tidak valid, coba lagi.")

    # Input manual
    print("\n--- Input Teman Secara Manual ---")
    chat_id_str = input("Masukkan Chat ID Telegram teman: ").strip()
    if not chat_id_str.isdigit():
        print("[X] Chat ID harus berupa angka.")
        return None
    name = input("Masukkan Nama Teman: ").strip() or "Teman"
    username = input("Masukkan Username Telegram teman (opsional, tanpa @): ").strip().replace("@", "")
    return int(chat_id_str), name, username

def run_auto_login_teman():
    target_info = get_target_friend()
    if not target_info:
        print("\n[!] Dibatalkan.")
        return False

    target_chat_id, target_name, target_username = target_info

    edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(edge_path):
        edge_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        if not os.path.exists(edge_path):
            print("[!] Browser Edge / Chrome tidak ditemukan.")
            return False

    # Gunakan profile khusus teman agar tidak bentrok dengan akun admin
    user_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "edge_teman_profile"))

    # Bersihkan profile lama jika ingin fresh login
    if os.path.exists(user_data):
        try:
            shutil.rmtree(user_data, ignore_errors=True)
        except Exception:
            pass

    print("\n" + "=" * 65)
    print(f"   🔑 MENGHUBUNGKAN AKUN UNTUK: {target_name.upper()} (ID: {target_chat_id})")
    print("=" * 65)
    print("[*] Membuka jendela login Classroom ITATS...")
    print(f"[*] Silakan ketik NPM & Password akun milik {target_name} di jendela browser.")
    print("[*] Begitu berhasil login, jendela akan otomatis tertutup sendiri!\n")

    proc = subprocess.Popen([
        edge_path,
        '--remote-debugging-port=9222',
        '--remote-allow-origins=*',
        f'--user-data-dir={user_data}',
        '--app=https://classroom.itats.ac.id/login'
    ])

    time.sleep(3)
    ws = None
    captured_session = ""
    captured_xsrf = ""
    captured_cf = ""
    session_found = False

    start_time = time.time()
    try:
        while time.time() - start_time < 300:  # Timeout 5 menit
            time.sleep(1.5)
            try:
                tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=3).read().decode())
                if not tabs:
                    continue

                target_tab = None
                for t in tabs:
                    if 'classroom' in t.get('url', '') or 'login' in t.get('url', ''):
                        target_tab = t
                        break
                if not target_tab:
                    target_tab = tabs[0]

                if ws is None:
                    try:
                        ws = websocket.create_connection(target_tab['webSocketDebuggerUrl'], timeout=3)
                    except Exception:
                        continue

                # Cek URL saat ini
                ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href'}}))
                res = json.loads(ws.recv())
                current_url = res.get('result', {}).get('result', {}).get('value', '')

                # Jika sudah berhasil masuk ke dashboard mahasiswa
                if 'mahasiswa' in current_url and 'login' not in current_url:
                    print(f"\n[+] Login berhasil untuk {target_name}! Mengambil cookie sesi...")

                    ws.send(json.dumps({'id': 2, 'method': 'Network.getCookies', 'params': {'urls': ['https://classroom.itats.ac.id']}}))
                    c_res = json.loads(ws.recv())
                    cookies = c_res.get('result', {}).get('cookies', [])
                    for c in cookies:
                        if c['name'] == 'classroom_itats_session':
                            captured_session = c['value']
                        elif c['name'] == 'XSRF-TOKEN':
                            captured_xsrf = c['value']
                        elif c['name'] == 'cf_clearance':
                            captured_cf = c['value']

                    if captured_session:
                        session_found = True
                        break
            except (websocket.WebSocketException, ConnectionResetError, BrokenPipeError):
                if ws:
                    try:
                        ws.close()
                    except Exception:
                        pass
                ws = None
            except Exception:
                pass

        if session_found:
            print("[+] Cookie berhasil diambil!")
            print("[*] Memverifikasi data tugas ke server Classroom ITATS...")

            count, new_session, new_xsrf, is_expired = itats_service.check_tasks(
                captured_session,
                captured_xsrf,
                captured_cf
            )

            active_session = new_session if new_session else captured_session
            active_xsrf = new_xsrf if new_xsrf else captured_xsrf

            # Simpan ke Database SQLite khusus teman ini (role="custom")
            database.save_or_update_user(
                chat_id=target_chat_id,
                name=target_name,
                username=target_username,
                session=active_session,
                xsrf=active_xsrf,
                cf_clearance=captured_cf,
                role="custom"
            )
            if count is not None:
                database.update_last_task_count(target_chat_id, count)

            # Kirim notifikasi Telegram langsung ke HP teman
            notif_text = (
                f"🎉 *AKUN CLASSROOM BERHASIL DIHUBUNGKAN!*\n\n"
                f"Halo *{target_name}*, akun Classroom ITATS pribadimu telah berhasil dihubungkan secara otomatis!\n\n"
                f"📚 *Tugas Belum Selesai Saat Ini:* {count if count is not None else 0} tugas\n"
                f"⏱️ *Interval Pemantauan:* Setiap 15 menit\n\n"
                f"Mulai sekarang bot akan otomatis memantau jadwal presensi dan tugas kuliah khusus untuk jurusan/kelasmu.\n"
                f"Ketik **/cek** kapan saja untuk mengecek tugas & presensi hari ini!"
            )
            send_telegram_msg(target_chat_id, notif_text)

            print("=" * 65)
            print("   ✅ SUKSES BESAR! AKUN TEMAN BERHASIL DIHUBUNGKAN!   ")
            print(f"   👤 Nama        : {target_name}")
            print(f"   🆔 Chat ID     : {target_chat_id}")
            print(f"   📚 Tugas Aktif : {count if count is not None else 0} tugas")
            print("   📲 Notifikasi sukses telah dikirim ke Telegram teman!")
            print("=" * 65)
            return True
        else:
            print("\n[!] Waktu login habis atau jendela browser ditutup.")
            return False

    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass
        try:
            proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    run_auto_login_teman()
