import subprocess
import json
import re
from typing import Optional, Tuple, List, Dict
from bs4 import BeautifulSoup

BASE_URL = "https://classroom.itats.ac.id"
ENDPOINT_TUGAS = f"{BASE_URL}/mahasiswa/getTugasBelumSelesai"
ENDPOINT_HOME = f"{BASE_URL}/mahasiswa/home"

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0"

def clean_cookie_val(val: str) -> str:
    if not val:
        return ""
    # Hapus karakter escaping Windows CMD (^%^3D -> %3D)
    val = val.replace("^%^3D", "%3D").replace("^", "").strip().strip('"').strip("'")
    return val

def parse_curl_command(text: str) -> Dict[str, str]:
    """
    Mengekstrak cookies dan User-Agent dari teks cURL yang di-paste user.
    """
    result = {
        "session": "",
        "xsrf": "",
        "cf_clearance": "",
        "user_agent": DEFAULT_USER_AGENT
    }

    # Cari classroom_itats_session
    m_session = re.search(r'classroom_itats_session=([^;\"\'\s]+)', text)
    if m_session:
        result["session"] = clean_cookie_val(m_session.group(1))

    # Cari XSRF-TOKEN
    m_xsrf = re.search(r'XSRF-TOKEN=([^;\"\'\s]+)', text)
    if m_xsrf:
        result["xsrf"] = clean_cookie_val(m_xsrf.group(1))

    # Cari cf_clearance
    m_cf = re.search(r'cf_clearance=([^;\"\'\s]+)', text)
    if m_cf:
        result["cf_clearance"] = clean_cookie_val(m_cf.group(1))

    # Cari User-Agent
    m_ua = re.search(r'User-Agent:\s*([^\"\'\r\n]+)', text, re.IGNORECASE)
    if m_ua:
        result["user_agent"] = m_ua.group(1).replace("^", "").strip()

    return result

def check_tasks(session: str, xsrf: str = "", cf_clearance: str = "", user_agent: str = DEFAULT_USER_AGENT) -> Tuple[Optional[int], str, str, bool]:
    """
    Mengecek jumlah tugas belum selesai via endpoint API.
    Return: (count, new_session, new_xsrf, is_expired)
    """
    if not session:
        return None, "", "", True

    cookie_list = [f"classroom_itats_session={session}"]
    if xsrf:
        cookie_list.append(f"XSRF-TOKEN={xsrf}")
    if cf_clearance:
        cookie_list.append(f"cf_clearance={cf_clearance}")
    cookie_str = "; ".join(cookie_list)

    cmd = [
        "curl.exe", "-s", "-i",
        "-H", f"User-Agent: {user_agent or DEFAULT_USER_AGENT}",
        "-H", "x-requested-with: XMLHttpRequest",
        "-H", "Accept: application/json, text/javascript, */*; q=0.01",
        "-H", f"Referer: {ENDPOINT_HOME}",
        "-b", cookie_str,
        ENDPOINT_TUGAS
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        raw = proc.stdout

        if "login" in raw or "Redirecting" in raw:
            return None, "", "", True

        parts = re.split(r'\r?\n\r?\n', raw)
        header_text = parts[0] if len(parts) > 0 else ""
        body_text = parts[-1].strip() if len(parts) > 1 else raw.strip()

        # Ekstrak auto keep-alive cookies
        new_cookies = dict(re.findall(r'Set-Cookie:\s*([^=]+)=([^;]+)', header_text, re.IGNORECASE))
        new_session = new_cookies.get("classroom_itats_session", "")
        new_xsrf = new_cookies.get("XSRF-TOKEN", "")

        data = json.loads(body_text)
        count = data.get("count", 0)
        return count, new_session, new_xsrf, False
    except Exception as e:
        print(f"[!] Error saat check_tasks: {e}")
        return None, "", "", False

def check_presensi(session: str, xsrf: str = "", cf_clearance: str = "", user_agent: str = DEFAULT_USER_AGENT) -> Tuple[Optional[List[Dict]], bool]:
    """
    Mengecek presensi kuliah yang sedang dibuka di Classroom ITATS.
    Return: (list_of_presensi, is_expired)
    """
    if not session:
        return None, True

    cookie_list = [f"classroom_itats_session={session}"]
    if xsrf:
        cookie_list.append(f"XSRF-TOKEN={xsrf}")
    if cf_clearance:
        cookie_list.append(f"cf_clearance={cf_clearance}")
    cookie_str = "; ".join(cookie_list)

    cmd = [
        "curl.exe", "-s",
        "-H", f"User-Agent: {user_agent or DEFAULT_USER_AGENT}",
        "-H", f"Referer: {BASE_URL}/login",
        "-b", cookie_str,
        ENDPOINT_HOME
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        html = proc.stdout

        if "login" in html or "Redirecting" in html:
            return None, True

        soup = BeautifulSoup(html, "html.parser")
        cols = soup.find_all("div", class_="student-activity-column")
        if len(cols) < 2:
            return [], False

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
        return hasil, False
    except Exception as e:
        print(f"[!] Error saat check_presensi: {e}")
        return [], False
