"""
Single-Command Local & LAN Institutional Placement Engine Launcher.
Detects LAN network interface, runs migrations, verifies frontend assets,
and launches the unified offline server.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def get_primary_lan_ip() -> str:
    """Detects active physical LAN IPv4 address without making outbound internet connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Routing table lookup to private IP space without sending packets
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
        # Prefer physical / non-VMware interfaces
        for ip in candidates:
            if not ip.startswith("127.") and not ip.startswith("169.254.") and not ip.startswith("192.168.65.") and not ip.startswith("192.168.83."):
                return ip
        for ip in candidates:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        return "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def get_all_lan_ips() -> list[str]:
    """Returns all reachable non-loopback IPv4 addresses."""
    try:
        hostname = socket.gethostname()
        candidates = socket.gethostbyname_ex(hostname)[2]
        return [ip for ip in candidates if not ip.startswith("127.") and not ip.startswith("169.254.")]
    except Exception:
        return [get_primary_lan_ip()]


def print_banner(lan_ip: str, port: int = 8000) -> None:
    all_ips = get_all_lan_ips()
    is_offline = (lan_ip == "127.0.0.1" and len([ip for ip in all_ips if ip != "127.0.0.1"]) == 0)
    print("=" * 76)
    print("   INSTITUTIONAL PLACEMENT ELIGIBILITY & SCHEDULING ENGINE")
    if is_offline:
        print("   100% OFFLINE STANDALONE MODE (NO NETWORK REQUIRED)")
    else:
        print("   HYBRID PUBLIC CLOUD & INSTITUTIONAL NETWORK DEPLOYMENT")
    print("=" * 76)
    print(f"   [+] Status:              ONLINE (READY FOR TRAFFIC)")
    if is_offline:
        print(f"   [+] Network:             OFFLINE (NO INTERNET OR LAN REQUIRED)")
    else:
        print(f"   [+] Network:             CONNECTED ({lan_ip})")
    print(f"   [+] Security:            Role-Based RBAC & Encrypted Student PII")
    print(f"   [+] Storage Engine:      SQLite WAL Mode (Local Database)")
    print(f"   [+] Constraint Solver:   Google OR-Tools CP-SAT (Local In-Memory)")
    print("   " + "-" * 70)
    print(f"   --> Local Browser URL:    http://localhost:{port}")
    if not is_offline:
        print(f"   --> Primary LAN Access:   http://{lan_ip}:{port}")
        for alt_ip in all_ips:
            if alt_ip != lan_ip and not alt_ip.startswith("192.168.65.") and not alt_ip.startswith("192.168.83."):
                print(f"   --> Alternate LAN/Hotspot: http://{alt_ip}:{port}")
        print("   " + "-" * 70)
        print(f"   SHARE THIS LINK WITH ANYONE ON YOUR WI-FI / LAN NETWORK:")
        print(f"   >>> http://{lan_ip}:{port} <<<")
    else:
        print(f"   --> Alternate Loopback:   http://127.0.0.1:{port}")
        print("   " + "-" * 70)
        print("   [!] OFFLINE STANDALONE: Running 100% locally on this machine.")
        print(f"   [!] Open http://localhost:{port} in any browser (Chrome, Edge, Firefox).")
    print("   " + "-" * 70)
    print("   Default Officer Login:    username='officer', password='officer123'")
    print("   Default Student Login:    roll_no='BT210001' or 'PIPE_001', code='123456'")
    print("=" * 76)
    sys.stdout.flush()


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    # 1. Run migrations
    print("[*] Verifying database schema and migrations...")
    try:
        subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], check=True)
    except Exception as exc:
        print(f"[!] Migration notice: {exc}. Verifying schema directly...")
        from backend.app.storage.database import Base, engine
        Base.metadata.create_all(bind=engine)

    # 2. Seed baseline accounts
    print("[*] Seeding default institutional accounts...")
    from backend.app.api.auth.seeder import seed_default_accounts
    seed_default_accounts()

    # 3. Check frontend dist
    dist_index = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist/index.html"))
    if not os.path.exists(dist_index):
        print("[*] Compiled frontend not found. Building production bundle...")
        subprocess.run(["npm", "run", "build"], cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend")), check=True)

    lan_ip = get_primary_lan_ip()
    print_banner(lan_ip, port)

    # 4. Optional browser auto-open
    if os.getenv("AUTO_OPEN_BROWSER", "0") == "1":
        try:
            import threading
            import time
            import webbrowser

            def _open():
                time.sleep(1.2)
                webbrowser.open(f"http://localhost:{port}")

            threading.Thread(target=_open, daemon=True).start()
        except Exception:
            pass

    # 5. Launch unified server
    import uvicorn
    uvicorn.run("backend.app.api.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
