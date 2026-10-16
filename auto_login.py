import subprocess
import json
import time
import os
import urllib.request
import websocket
from dotenv import load_dotenv

import database

def update_env_file(session: str, xsrf: str, cf: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    updates = {
        "CLASSROOM_SESSION": session,
        "XSRF_TOKEN": xsrf,
        "CF_CLEARANCE": cf
    }

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        found_keys = set()
        for line in lines:
            matched = False
            for k, v in updates.items():
                if line.startswith(f"{k}="):
                    new_lines.append(f"{k}={v}\n")
                    found_keys.add(k)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)

        for k, v in updates.items():
            if k not in found_keys:
                new_lines.append(f"{k}={v}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[!] Gagal menulis ke .env: {e}")

def run_auto_login():
    edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    if not os.path.exists(edge_path):
        # Fallback ke Chrome jika Edge tidak ada
        edge_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
        if not os.path.exists(edge_path):
            print("[!] Browser Edge / Chrome tidak ditemukan.")
            return False

    user_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "edge_login_profile"))
    
    print("=" * 60)
    print("   🔑 LOGIN OTOMATIS CLASSROOM ITATS (AUTO-GRAB COOKIE)   ")
    print("=" * 60)
    print("[*] Membuka jendela login Classroom ITATS...")
    print("[*] Silakan ketik NPM & Password kamu di jendela yang muncul.")
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

                # Hubungkan WebSocket jika belum atau terputus
                if ws is None:
                    try:
                        ws = websocket.create_connection(target_tab['webSocketDebuggerUrl'], timeout=3)
                    except Exception:
                        continue

                # Cek URL saat ini
                ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': 'window.location.href'}}))
                res = json.loads(ws.recv())
                current_url = res.get('result', {}).get('result', {}).get('value', '')

                # Jika sudah masuk ke halaman dashboard mahasiswa
                if 'mahasiswa' in current_url and 'login' not in current_url:
                    print("\n[+] Berhasil login terdeteksi! Mengambil cookie otomatis...")
                    
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
            print("[+] Cookie berhasil diambil secara otomatis!")
            # 1. Update ke file .env
            update_env_file(captured_session, captured_xsrf, captured_cf)
            
            # 2. Update ke Database SQLite
            database.init_db()
            admin = database.get_admin_user()
            admin_cid = admin["chat_id"] if admin else int(os.getenv("TELEGRAM_CHAT_ID", "0"))
            if admin_cid:
                database.save_or_update_user(
                    chat_id=admin_cid,
                    name="Aryo (Admin)",
                    username="aryosyarif",
                    session=captured_session,
                    xsrf=captured_xsrf,
                    cf_clearance=captured_cf,
                    role="admin"
                )

            print("=" * 60)
            print("   ✅ SESI CLASSROOM BERHASIL DIPERBARUI OTOMATIS!   ")
            print("   Sekarang kamu bisa langsung jalankan bot (run.bat)")
            print("=" * 60)
            return True
        else:
            print("\n[!] Waktu login habis atau jendela ditutup.")
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
    run_auto_login()
