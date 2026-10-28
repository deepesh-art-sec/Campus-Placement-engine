"""
Standalone Windows Executable Launcher for Institutional Placement Engine.
Auto-hosts on Localhost and LAN simultaneously, provisions persistent SQLite store,
and auto-opens the web application in the default browser.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import webbrowser

# Determine if running in frozen PyInstaller bundle or standard Python
if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    EXE_DIR = BUNDLE_DIR

if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

# Configure Windows DLL resolution for OR-Tools C++ bindings
def _setup_dlls(base_dir: str) -> None:
    ortools_libs = os.path.join(base_dir, "ortools", ".libs")
    dirs_to_add = [base_dir, ortools_libs]
    for d in dirs_to_add:
        if os.path.isdir(d):
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
            os.environ["PATH"] = d + ";" + os.environ.get("PATH", "")

    # Preload native dependencies in strict dependency order
    if os.path.isdir(ortools_libs):
        import ctypes
        dll_sequence = [
            "zlib1.dll",
            "bz2.dll",
            "libutf8_validity.dll",
            "abseil_dll.dll",
            "re2.dll",
            "libprotobuf.dll",
            "highs.dll",
            "libscip.dll",
            "ortools.dll",
        ]
        for dll_name in dll_sequence:
            candidate = os.path.join(ortools_libs, dll_name)
            if os.path.isfile(candidate):
                try:
                    ctypes.WinDLL(candidate)
                except Exception:
                    pass

_setup_dlls(BUNDLE_DIR)

# 1. Configure Persistent Database
target_db = os.path.join(EXE_DIR, "placement_engine.db")
bundled_db = os.path.join(BUNDLE_DIR, "placement_engine.db")

if not os.path.exists(target_db):
    if os.path.exists(bundled_db):
        print(f"[*] Provisioning fresh database template to: {target_db}")
        shutil.copy2(bundled_db, target_db)
    else:
        print(f"[*] Database file will be created at: {target_db}")

# Force database engine to use persistent directory next to the exe
clean_db_path = target_db.replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite:///{clean_db_path}"

# 2. Configure Static Frontend SPA Bundle
frontend_dist = os.path.join(BUNDLE_DIR, "frontend", "dist")
if os.path.exists(frontend_dist):
    os.environ["FRONTEND_DIST_DIR"] = frontend_dist


def get_primary_lan_ip() -> str:
    """Detects active physical LAN IPv4 address without making outbound internet connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
            return ip
    except Exception:
        pass
    finally:
        s.close()

    try:
        hostname = socket.gethostname()
        candidates = socket.gethostbyname_ex(hostname)[2]
        for ip in candidates:
            if not ip.startswith("127.") and not ip.startswith("169.254.") and not ip.startswith("192.168.65."):
                return ip
        for ip in candidates:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        return "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def get_all_lan_ips() -> list[str]:
    """Returns all non-loopback IPv4 addresses."""
    try:
        hostname = socket.gethostname()
        candidates = socket.gethostbyname_ex(hostname)[2]
        return [ip for ip in candidates if not ip.startswith("127.") and not ip.startswith("169.254.")]
    except Exception:
        return [get_primary_lan_ip()]


def print_banner(lan_ip: str, port: int) -> None:
    all_ips = get_all_lan_ips()
    print("=" * 76)
    print("   INSTITUTIONAL PLACEMENT ELIGIBILITY & SCHEDULING ENGINE")
    print("   STANDALONE DESKTOP & LAN HYBRID HOST")
    print("=" * 76)
    print("   [+] Status:              ONLINE (LISTENING ON ALL INTERFACES)")
    print(f"   [+] Primary LAN IP:      {lan_ip}")
    print(f"   [+] Persistent Database: {target_db}")
    print(f"   [+] Security:            Air-Gap Ready, Zero Outbound Telemetry")
    print("   " + "-" * 70)
    print(f"   --> Local Computer URL:   http://localhost:{port}")
    print(f"   --> Loopback URL:         http://127.0.0.1:{port}")
    if lan_ip != "127.0.0.1":
        print(f"   --> Primary LAN Access:   http://{lan_ip}:{port}")
        for alt in all_ips:
            if alt != lan_ip and not alt.startswith("192.168.65."):
                print(f"   --> Alternate LAN URL:    http://{alt}:{port}")
        print("   " + "-" * 70)
        print("   SHARE THIS LINK WITH STUDENTS, COORDINATORS & RECRUITERS ON LAN/WI-FI:")
        print(f"   >>> http://{lan_ip}:{port} <<<")
    print("   " + "-" * 70)
    print("   Default Officer Login:     username='officer', password='officer123'")
    print("   Default Coordinator Login: username='coordinator', password='coord123'")
    print("   Default Recruiter Login:   username='recruiter_google', password='recruiter123'")
    print("   Default Student Login:     roll_no='BT210001', code='123456'")
    print("=" * 76)
    sys.stdout.flush()


def open_browser_delayed(url: str, delay: float = 1.2) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0"

    # Seed baseline default accounts
    try:
        from backend.app.api.auth.seeder import seed_default_accounts
        seed_default_accounts()
    except Exception as exc:
        print(f"[!] Warning during baseline account check: {exc}")

    lan_ip = get_primary_lan_ip()
    print_banner(lan_ip, port)

    # Automatically launch browser on localhost
    if os.getenv("NO_BROWSER", "0") != "1":
        threading.Thread(target=open_browser_delayed, args=(f"http://localhost:{port}",), daemon=True).start()

    # Launch Uvicorn with the FastAPI application
    import uvicorn
    from backend.app.api.main import app
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
