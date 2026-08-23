#!/usr/bin/env python3

'''
/----------------------*-------------------------\
     Made & Developed by @calebdev on tele
     Title: (Idle) <VERO_APP> — V<VERSION>   |  env: VERO_APP, VERO_COLS, VERO_LINES
/------------------------------------------------\
'''

import math
import os, platform, sys, re, json, time, base64, shutil, unicodedata, subprocess, webbrowser, requests
from typing import Optional
from urllib.parse import quote, urlparse
from colorama import Style, init

VERSION = "1.1.3"

init(autoreset=True)

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

_TERMINAL_READY = False


def _pause_for_menu() -> None:
    """Wait for Enter before returning to the main menu."""
    tw = _term_cols()
    hint = _center_plain_line("Press Enter to continue", tw)
    print(f"\n{Style.DIM}{hint}{Style.RESET_ALL}")
    if os.name == "nt":
        try:
            import msvcrt

            while True:
                if msvcrt.kbhit():
                    k = msvcrt.getch()
                    if k in (b"\r", b"\n"):
                        return
                time.sleep(0.03)
        except Exception:
            try:
                input()
            except EOFError:
                return
            return
    try:
        import select

        while True:
            r, _, _ = select.select([sys.stdin], [], [], 0.12)
            if r:
                try:
                    sys.stdin.readline()
                except Exception:
                    pass
                return
    except Exception:
        try:
            input()
        except EOFError:
            return


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _str_display_width(s: str) -> int:
    s = _strip_ansi(s)
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _set_terminal_title() -> None:
    """Windows: `title (Idle) … — V…` (cmd-style). Other: OSC 0."""
    app = (os.environ.get("VERO_APP") or "Vero").strip() or "Vero"
    app = re.sub(r'[<>&|\r\n"]', "", app)[:64]
    if os.name == "nt":
        try:
            os.system(f"title (Idle) {app} — V{VERSION} ")
        except Exception:
            try:
                import ctypes

                ctypes.windll.kernel32.SetConsoleTitleW(f"(Idle) {app} — V{VERSION}")
            except Exception:
                pass
    else:
        try:
            t = f"(Idle) {app} — V{VERSION}"
            sys.stdout.write("\033]0;" + t.replace("\007", "") + "\007")
            sys.stdout.flush()
        except Exception:
            pass


def _resize_console_compact() -> None:
    """Narrow console (phone-ish) on Windows via `mode con` — env VERO_COLS / VERO_LINES."""
    if os.name != "nt":
        return
    try:
        cols = int(os.environ.get("VERO_COLS", "52"))
        lines = int(os.environ.get("VERO_LINES", "32"))
    except ValueError:
        cols, lines = 52, 32
    cols = max(40, min(cols, 120))
    lines = max(24, min(lines, 90))
    try:
        os.system(f"mode con: cols={cols} lines={lines}")
    except Exception:
        pass


def _hard_reset_terminal() -> None:
    """Clear screen before menu (uses host `cls` / `clear`)."""
    try:
        sys.stdout.write("\033[0m")
        sys.stdout.flush()
    except Exception:
        pass
    if platform.system() == "Windows":
        import winreg
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def _ensure_terminal() -> None:
    """UTF-8 + virtual terminal so box-drawing, truecolor rainbow, and emojis render cleanly."""
    global _TERMINAL_READY
    if _TERMINAL_READY:
        return
    _TERMINAL_READY = True
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleInputCP(65001)
            kernel32 = ctypes.windll.kernel32
            STD_OUTPUT_HANDLE = -11
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
                kernel32.SetConsoleMode(h, mode)
        except Exception:
            pass
        try:
            os.system("")
        except Exception:
            pass
        _resize_console_compact()


EXCHANGE_API = (
    "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/exchange"
)


def epic_exchange_url(code: str) -> str:
    return f"https://www.epicgames.com/id/exchange?exchangeCode={quote(code, safe='')}"


def _fortnite_exchange_launch_cmd(exchange_code: str, epic_account_id: str) -> str:
    """Windows cmd line: FortniteLauncher with exchangecode auth (matches Epic Win64 install layout)."""
    win64 = r"C:\Program Files\Epic Games\Fortnite\FortniteGame\Binaries\Win64"
    return (
        f'start /d "{win64}" FortniteLauncher.exe -AUTH_LOGIN=unused '
        f"-AUTH_PASSWORD={exchange_code} -AUTH_TYPE=exchangecode "
        f"-epicapp=Fortnite -epicenv=Prod -EpicPortal -epicuserid={epic_account_id} & exit"
    )


def _is_fortnite_shop_url(url: str) -> bool:
    """True if string looks like an http(s) Fortnite / Epic web shop URL."""
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        return False
    try:
        p = urlparse(u)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if not (host == "fortnite.com" or host.endswith(".fortnite.com") or "epicgames.com" in host):
            return False
        path = (p.path or "").lower()
        return "item-shop" in path or "item_shop" in path or bool(re.search(r"/[a-z0-9]+-[a-f0-9]{8}", u, re.I))
    except Exception:
        return False


def _item_slug_from_shop_url(url: str) -> Optional[str]:
    """Last URL segment, lowercased, minus the trailing 6–12 hex id (e.g. `kongs-battle-axe-e17f70eb` → `kongs-battle-axe`)."""
    try:
        path = (urlparse(url).path or "").rstrip("/")
    except Exception:
        return None
    if not path:
        return None
    last = path.rsplit("/", 1)[-1].lower().split("?", 1)[0]
    last = re.sub(r"-[a-f0-9]{6,12}$", "", last)
    return last or None


def _slugify_name(s: str) -> str:
    """Lowercase ASCII slug for matching; strips apostrophes & non-alnum."""
    s = (s or "").lower().replace("'", "").replace("\u2019", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def _best_entry_display_name(e: dict) -> str:
    """Longest human-readable shop title (avoids short bundle labels like 'Kong')."""
    names: list[str] = []
    for item in e.get("brItems") or []:
        n = item.get("name")
        if n and str(n).strip():
            names.append(str(n).strip())
    b = (e.get("bundle") or {}).get("name")
    if b and str(b).strip():
        names.append(str(b).strip())
    for k in ("instruments", "cars", "legoKits"):
        for item in e.get(k) or []:
            n = item.get("name")
            if n and str(n).strip():
                names.append(str(n).strip())
    dev = e.get("devName") or ""
    m = re.search(r"\d+\s*x\s+([^f]+?)\s+for\s+\d+", dev, re.I)
    if m:
        names.append(m.group(1).strip())
    if names:
        return max(names, key=len)
    ly = (e.get("layout") or {}).get("name")
    if ly:
        return str(ly).strip()
    return (dev or "").strip() or "?"


def _shop_category_label(url: str) -> Optional[str]:
    """Segment after /item-shop/ in the web URL (e.g. pickaxes → Pickaxes). Skips generic offers/bundles."""
    try:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    except Exception:
        return None
    for i, p in enumerate(parts):
        if p.lower() in ("item-shop", "item_shop") and i + 1 < len(parts):
            seg = parts[i + 1]
            sl = seg.lower()
            if sl in ("offers", "offer", "bundles", "bundle"):
                return None
            t = seg.replace("-", " ").strip().title()
            return t or None
    return None


def fetch_exchange_code(access_token: str) -> Optional[str]:
    r = requests.get(
        EXCHANGE_API,
        headers={"Authorization": "Bearer " + access_token},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    return r.json().get("code")


def _term_cols() -> int:
    try:
        return max(40, shutil.get_terminal_size().columns)
    except Exception:
        return 80


_GIFT_MARGIN = "  "


def _gift_note(msg: str) -> None:
    """Dim line for the gift flow; left-aligned so wide terminals do not split label from input."""
    print(f"{_GIFT_MARGIN}{Style.DIM}{msg}{Style.RESET_ALL}")


def _gift_ask() -> str:
    return input(f"{_GIFT_MARGIN}{Style.DIM}>{Style.RESET_ALL} ").strip()


def _center_plain_line(line: str, width: int) -> str:
    """Center using display width so lolcat / ANSI is not sliced mid-escape."""
    vw = _str_display_width(line)
    if vw > width:
        plain = _strip_ansi(line)
        ell = "…"
        while plain and _str_display_width(plain + ell) > width:
            plain = plain[:-1]
        line = plain + ell if plain else ell[:width]
        vw = _str_display_width(line)
    pad_l = max(0, (width - vw) // 2)
    pad_r = max(0, width - vw - pad_l)
    return " " * pad_l + line + " " * pad_r


def _lolcat_paint(text: str, freq: float = 0.14, spread: float = 3.4) -> str:
    """Truecolor rainbow similar to Ruby `lolcat` (works without the lolcat binary)."""
    out_lines: list[str] = []
    y = 0
    for line in text.split("\n"):
        parts: list[str] = []
        for x, ch in enumerate(line):
            if ch == " ":
                parts.append(ch)
                continue
            t = x * spread + y
            r = int(127 + 127 * math.sin(freq * t))
            g = int(127 + 127 * math.sin(freq * t + 2 * math.pi / 3))
            b = int(127 + 127 * math.sin(freq * t + 4 * math.pi / 3))
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            parts.append(f"\033[38;2;{r};{g};{b}m{ch}")
        parts.append("\033[0m")
        out_lines.append("".join(parts))
        y += 1
    return "\n".join(out_lines)


def _print_rainbow_url(url: str, tw: int) -> None:
    """Rainbow URL without truncation; center only when it fits (long URLs wrap in the terminal)."""
    ln = _lolcat_paint(url)
    vw = _str_display_width(ln)
    if vw < tw:
        print(" " * max(0, (tw - vw) // 2) + ln)
    else:
        print(ln)


def _say(msg: str, indent: str = "    ") -> None:
    """Status line: truecolor rainbow (same as logo), not a fixed magenta accent."""
    print(indent + _lolcat_paint(msg))


# Centered box logo (rainbow); decorative band matches the requested style.
_LOGO_PLAIN = [
    "        ┏  ",
    "┓┏┏┓┏┓┏┓╋┏┓",
    "┗┛┗ ┛ ┗┛┛┛┗",
]


def _logo_block_for_width(tw: int) -> str:
    mw = max(len(s) for s in _LOGO_PLAIN)
    inner = min(max(mw + 4, 28), tw - 2)
    inner = max(inner, mw)
    lines = [_center_plain_line(s, inner) for s in _LOGO_PLAIN]
    return "\n".join(_center_plain_line(line, tw) for line in lines)


def _rainbow_separator_line(tw: int) -> str:
    line = "─" * max(8, tw)
    if len(line) > tw:
        line = line[:tw]
    return _lolcat_paint(_center_plain_line(line, tw))


def _rainbow_char(ch: str, t: float) -> str:
    r = int(127 + 127 * math.sin(0.14 * t))
    g = int(127 + 127 * math.sin(0.14 * t + 2 * math.pi / 3))
    b = int(127 + 127 * math.sin(0.14 * t + 4 * math.pi / 3))
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return f"\033[38;2;{r};{g};{b}m{ch}\033[0m"


def _bracket_glyph(sym: str, phase: float) -> str:
    mid = _rainbow_char(sym, phase)
    return f"{Style.DIM}[{Style.RESET_ALL}{mid}{Style.DIM}]{Style.RESET_ALL}"


def _menu_row_sym(sym: str, label: str, key: str, inner: int, phase: float) -> str:
    left = f"{_bracket_glyph(sym, phase)}{Style.DIM} > {label}{Style.RESET_ALL}"
    gap = inner - _str_display_width(left) - len(key)
    gaps = max(1, gap)
    return left + f"{Style.DIM}{' ' * gaps}{key}{Style.RESET_ALL}"


def _account_index_glyph(idx: int, phase: float) -> str:
    """Rainbow bracketed slot index (multi-digit safe)."""
    s = str(idx)
    if len(s) == 1:
        return _bracket_glyph(s, phase)
    mid = "".join(_rainbow_char(c, phase + j * 0.65) for j, c in enumerate(s))
    return f"{Style.DIM}[{Style.RESET_ALL}{mid}{Style.DIM}]{Style.RESET_ALL}"


def _account_list_row(idx: int, label: str, inner: int, phase: float, right: str = "") -> str:
    left = f"{_account_index_glyph(idx, phase)}{Style.DIM} > {label}{Style.RESET_ALL}"
    gap = inner - _str_display_width(left) - len(right)
    gaps = max(1, gap)
    return left + f"{Style.DIM}{' ' * gaps}{right}{Style.RESET_ALL}"


def _truncate_visible(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    if max_chars == 1:
        return "…"
    return s[: max_chars - 1] + "…"


# Type the bracket symbol or the digit (same as key).
_MENU_SYM_TO_KEY: dict[str, str] = {
    "+": "1",
    "-": "2",
    "#": "3",
    "=": "4",
    ">": "5",
    "*": "6",
    "x": "0",
    "X": "0",
}


def _normalize_menu_choice(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s in _MENU_SYM_TO_KEY:
        return _MENU_SYM_TO_KEY[s]
    if len(s) == 1 and s in "0123456":
        return s
    return s


def _fetch_epic_profile(a: dict) -> tuple[str, str]:
    display_name, email = "?", "N/A"
    try:
        did = base64.b64decode(a["deviceId"]).decode()
        sec = base64.b64decode(a["secret"]).decode()
        rr = requests.post(
            "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            headers={
                "Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "device_auth",
                "device_id": did,
                "account_id": a["accountId"],
                "secret": sec,
            },
            timeout=10,
        )
        if rr.status_code == 200:
            tok = rr.json().get("access_token")
            r2 = requests.get(
                f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{a['accountId']}",
                headers={"Authorization": "Bearer " + tok},
                timeout=10,
            )
            if r2.status_code == 200:
                dd = r2.json()
                display_name = dd.get("displayName") or dd.get("name") or "Unknown"
                email = dd.get("email") or "N/A"
    except Exception:
        pass
    return display_name, email


def _vbucks_from_common_core_query(access_token: str, account_id: str) -> Optional[int]:
    """Read-only common_core QueryProfile; sums Currency:Mtx balances."""
    try:
        url = (
            "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/"
            f"{account_id}/client/QueryProfile?profileId=common_core&rvn=-1"
        )
        r = requests.post(
            url,
            json={},
            headers={
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        changes = data.get("profileChanges") or []
        if not changes:
            return None
        prof = changes[0].get("profile") or {}
        items = prof.get("items") or {}
        total = 0
        for item in items.values():
            if not isinstance(item, dict):
                continue
            tid = str(item.get("templateId", ""))
            if tid.startswith("Currency:Mtx"):
                q = item.get("quantity")
                if q is not None:
                    total += int(q)
        return total
    except Exception:
        return None


def _format_last_played_mdy(v: object) -> str:
    """Epic lastLogin → short date like 4/26/25 (M/D/YY)."""
    if v is None:
        return "—"
    s = str(v).strip()
    if not s:
        return "—"
    try:
        date_part = s[:10]
        if len(date_part) >= 10 and date_part[4] == "-" and date_part[7] == "-":
            y = int(date_part[0:4])
            mo = int(date_part[5:7])
            d = int(date_part[8:10])
            return f"{mo}/{d}/{y % 100}"
    except Exception:
        pass
    return s[:10] if len(s) >= 10 else s


def _fetch_epic_single_view_fields(a: dict) -> tuple[str, str, str, str, str, Optional[int], str]:
    """One account: display name, email, account id, country code, last played (M/D/YY), vbucks or None, error."""
    try:
        did = base64.b64decode(a["deviceId"]).decode()
        sec = base64.b64decode(a["secret"]).decode()
        aid = a.get("accountId") or ""
        if not aid:
            return "?", "N/A", "", "—", "—", None, "Missing accountId."

        rr = requests.post(
            "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            headers={
                "Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "device_auth",
                "device_id": did,
                "account_id": aid,
                "secret": sec,
            },
            timeout=10,
        )
        if rr.status_code != 200:
            return "?", "N/A", aid, "—", "—", None, "Auth failed."
        tok = rr.json().get("access_token")
        if not tok:
            return "?", "N/A", aid, "—", "—", None, "Auth failed."

        r2 = requests.get(
            f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{aid}",
            headers={"Authorization": "Bearer " + tok},
            timeout=10,
        )
        if r2.status_code != 200:
            return "?", "N/A", aid, "—", "—", None, f"Account lookup failed ({r2.status_code})."

        dd = r2.json()
        dn = dd.get("displayName") or dd.get("name") or "Unknown"
        em = dd.get("email") or "N/A"
        country = str(dd.get("country") or "").strip() or "—"
        last_login = _format_last_played_mdy(dd.get("lastLogin"))
        vb = _vbucks_from_common_core_query(tok, aid)
        return dn, em, aid, country, last_login, vb, ""
    except Exception as e:
        aid = (a.get("accountId") or "") or ""
        return "?", "N/A", aid, "—", "—", None, (str(e) or "Failed.")


def _print_epic_profile_block(
    display_name: str,
    email: str,
    account_id: str,
    *,
    extended: bool = False,
    country: str = "",
    last_login: str = "",
    vbucks: Optional[int] = None,
) -> None:
    """Name / email / id; optional last played (M/D/YY) then '0 VB · US' style line when extended."""
    tw = _term_cols()
    print(_center_plain_line(_lolcat_paint(display_name), tw))
    print(_center_plain_line(f"{Style.DIM}{email}{Style.RESET_ALL}", tw))
    aid = account_id if len(account_id) <= tw - 4 else account_id[: max(8, tw - 8)] + "…"
    print(_center_plain_line(f"{Style.DIM}{aid}{Style.RESET_ALL}", tw))
    if extended:
        ll = last_login.strip() if last_login.strip() else "—"
        print(_center_plain_line(f"{Style.DIM}Last Played: {ll}{Style.RESET_ALL}", tw))
        c = country.strip() if country.strip() else "—"
        vb_part = f"{vbucks} VB" if vbucks is not None else "— VB"
        print(_center_plain_line(f"{Style.DIM}{vb_part} · {c}{Style.RESET_ALL}", tw))


def _prompt_main_menu() -> str:
    _ensure_terminal()
    tw = _term_cols()
    _set_terminal_title()

    logo_plain = _logo_block_for_width(tw)
    print(_lolcat_paint(logo_plain) + Style.RESET_ALL)
    ver_plain = _center_plain_line(f"v{VERSION}", tw)
    print(_lolcat_paint(ver_plain) + Style.RESET_ALL)
    print(_rainbow_separator_line(tw) + Style.RESET_ALL)
    print()

    menu_spec = [
        ("+", "Add Epic account", "1", 0.0),
        ("-", "Remove Epic account", "2", 2.0),
        ("#", "View Epic account", "3", 4.0),
        ("=", "Generate exchange code", "4", 6.0),
        (">", "Send gift item to user", "5", 8.0),
        ("*", "Quick launch Fortnite", "6", 10.0),
        ("x", "Exit", "0", 12.0),
    ]
    def _row_left_width(sym: str, lab: str, ph: float) -> int:
        s = f"{_bracket_glyph(sym, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
        return _str_display_width(s)

    inner = max(_row_left_width(s, lab, ph) + len(k) + 2 for s, lab, k, ph in menu_spec)
    inner = min(inner, tw - 4)
    inner = max(inner, 36)

    sections = [
        [
            _menu_row_sym("+", "Add Epic account", "1", inner, 0.0),
            _menu_row_sym("-", "Remove Epic account", "2", inner, 2.0),
            _menu_row_sym("#", "View Epic account", "3", inner, 4.0),
        ],
        [
            _menu_row_sym("=", "Generate exchange code", "4", inner, 6.0),
            _menu_row_sym(">", "Send gift item to user", "5", inner, 8.0),
            _menu_row_sym("*", "Quick launch Fortnite", "6", inner, 10.0),
        ],
        [
            _menu_row_sym("x", "Exit", "0", inner, 12.0),
        ],
    ]
    flat = [ln for sec in sections for ln in sec]
    mw = max(_str_display_width(ln) for ln in flat)
    first_sec = True
    for sec in sections:
        if not first_sec:
            print()
        first_sec = False
        for r in sec:
            pad = max(0, (tw - mw) // 2)
            print(" " * pad + r)

    print()

    prompt_plain = "> "
    pad = max(0, (tw - _str_display_width(prompt_plain)) // 2)
    raw = input(" " * pad + f"{Style.DIM}>{Style.RESET_ALL} ").strip()
    return _normalize_menu_choice(raw)


while True:
    _hard_reset_terminal()
    choice = _prompt_main_menu()

    if choice == "1":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs: list = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('Add Epic account  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}"
        )
        print()
        try:
            r = requests.post(
                "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={
                    "Authorization": "Basic OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "client_credentials"},
                timeout=15,
            ).json()
            tok_client = r.get("access_token")
            if not tok_client:
                raise ValueError(r.get("errorMessage") or r.get("error") or "no client token")
            auth = requests.post(
                "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/deviceAuthorization",
                headers={"Authorization": "Bearer " + tok_client},
                timeout=15,
            ).json()
            if not auth.get("device_code"):
                raise ValueError(auth.get("errorMessage") or auth.get("error") or "device auth failed")
        except Exception as e:
            _say(f"[!] Could not start device login: {e}")
            _pause_for_menu()
            continue
        vuri = (auth.get("verification_uri_complete") or auth.get("verification_uri") or "").strip()
        if vuri:
            print(_center_plain_line(_lolcat_paint(vuri), tw))
            print()
        else:
            print(f"{Style.DIM}{_center_plain_line('No sign-in link returned.', tw)}{Style.RESET_ALL}")
            print()
        with open(os.devnull, "w") as dn:
            _stderr_hold = sys.stderr
            sys.stderr = dn
            try:
                if vuri:
                    webbrowser.open(vuri)
            finally:
                sys.stderr = _stderr_hold
        account_id, access_token = "", ""
        while True:
            time.sleep(11)
            try:
                resp = requests.post(
                    "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    headers={
                        "Authorization": "Basic OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "device_code", "device_code": auth["device_code"]},
                    timeout=20,
                )
            except Exception as e:
                _say(f"[!] Network error while polling: {e}")
                _pause_for_menu()
                continue
            if resp.status_code != 400:
                try:
                    d = resp.json()
                except Exception:
                    _say("[!] Invalid response from Epic.")
                    _pause_for_menu()
                    break
                account_id = d.get("account_id") or ""
                access_token = d.get("access_token") or ""
                if account_id and access_token:
                    break
        if not account_id or not access_token:
            continue
        try:
            exch = requests.get(
                "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/exchange",
                headers={"Authorization": "Bearer " + access_token},
                timeout=15,
            ).json()["code"]
            tok = requests.post(
                "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={
                    "Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "exchange_code", "exchange_code": exch},
                timeout=15,
            ).json()["access_token"]
            dev = requests.post(
                f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}/deviceAuth",
                headers={"Authorization": "Bearer " + tok},
                timeout=15,
            ).json()
        except Exception as e:
            _say(f"[!] Could not finish device auth: {e}")
            _pause_for_menu()
            continue
        device_auth = {
            "accountId": account_id,
            "deviceId": base64.b64encode(dev["deviceId"].encode()).decode(),
            "secret": base64.b64encode(dev["secret"].encode()).decode(),
        }
        try:
            rr = requests.get(
                f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}",
                headers={"Authorization": "Bearer " + access_token},
                timeout=10,
            )
            if rr.status_code == 200:
                device_auth["displayName"] = rr.json().get("displayName") or rr.json().get("name") or "Unknown"
        except Exception:
            pass
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        if not any(a["accountId"] == device_auth["accountId"] for a in accs):
            accs.append(device_auth)
            with open("config.json", "w") as f:
                json.dump(accs, f, indent=4)
        print()
        dn, em = _fetch_epic_profile(device_auth)
        _print_epic_profile_block(dn, em, device_auth["accountId"])
        print()
        _pause_for_menu()

    elif choice == "2":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('Remove Epic account  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}"
        )
        print()
        if not accs:
            print(f"{Style.DIM}{_center_plain_line('No linked accounts yet.', tw)}{Style.RESET_ALL}")
            _pause_for_menu()
            continue
        max_lab = max(12, tw - 18)
        inner = 36
        for i, a in enumerate(accs):
            lab = _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab)
            ph = (i * 2.0) % 12.0
            left_only = f"{_account_index_glyph(i, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
            inner = max(inner, _str_display_width(left_only) + 2)
        account_lines = [
            _account_list_row(
                i,
                _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab),
                inner,
                (i * 2.0) % 12.0,
                "",
            )
            for i, a in enumerate(accs)
        ]
        mw = max(_str_display_width(ln) for ln in account_lines)
        for ln in account_lines:
            print(" " * max(0, (tw - mw) // 2) + ln)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('index 0–' + str(len(accs) - 1) + '  to remove', tw)}{Style.RESET_ALL}"
        )
        prompt_plain = "> "
        pad = max(0, (tw - _str_display_width(prompt_plain)) // 2)
        idx = input(" " * pad + f"{Style.DIM}>{Style.RESET_ALL} ").strip()
        if idx.isdigit() and 0 <= int(idx) < len(accs):
            accs.pop(int(idx))
            with open("config.json", "w") as f:
                json.dump(accs, f, indent=4)
            print()
            print(f"{Style.DIM}{_center_plain_line('Removed.', tw)}{Style.RESET_ALL}")
            print()
        else:
            print(
                f"{Style.DIM}{_center_plain_line('Use index 0–' + str(len(accs) - 1) + '.', tw)}{Style.RESET_ALL}"
            )
        _pause_for_menu()

    elif choice == "3":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('View Epic account  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}"
        )
        print()
        if not accs:
            print(f"{Style.DIM}{_center_plain_line('No linked accounts yet.', tw)}{Style.RESET_ALL}")
            _pause_for_menu()
            continue
        max_lab = max(12, tw - 18)
        inner = 36
        for i, a in enumerate(accs):
            lab = _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab)
            ph = (i * 2.0) % 12.0
            left_only = f"{_account_index_glyph(i, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
            inner = max(inner, _str_display_width(left_only) + 2)
        account_lines = [
            _account_list_row(
                i,
                _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab),
                inner,
                (i * 2.0) % 12.0,
                "",
            )
            for i, a in enumerate(accs)
        ]
        mw = max(_str_display_width(ln) for ln in account_lines)
        for ln in account_lines:
            print(" " * max(0, (tw - mw) // 2) + ln)
        print()
        print(f"{Style.DIM}{_center_plain_line('a all  ·  # one', tw)}{Style.RESET_ALL}")
        prompt_plain = "> "
        pad = max(0, (tw - _str_display_width(prompt_plain)) // 2)
        scope = input(" " * pad + f"{Style.DIM}>{Style.RESET_ALL} ").strip().lower()
        if scope in ("a", "all"):
            print()
            for idx, a in enumerate(accs):
                if idx > 0:
                    sw = min(44, max(16, tw - 8))
                    print(_center_plain_line(f"{Style.DIM}{'─' * sw}{Style.RESET_ALL}", tw))
                dn, em = _fetch_epic_profile(a)
                _print_epic_profile_block(dn, em, a["accountId"])
                print()
                time.sleep(0.08)
        elif scope.isdigit() and 0 <= int(scope) < len(accs):
            a = accs[int(scope)]
            print()
            dn, em, aid, ctry, llog, vb, err = _fetch_epic_single_view_fields(a)
            if err:
                print(f"{Style.DIM}{_center_plain_line(err, tw)}{Style.RESET_ALL}")
            else:
                _print_epic_profile_block(
                    dn,
                    em,
                    aid,
                    extended=True,
                    country=ctry,
                    last_login=llog,
                    vbucks=vb,
                )
            print()
        else:
            print(
                f"{Style.DIM}{_center_plain_line('a or all  ·  index 0–' + str(len(accs) - 1), tw)}{Style.RESET_ALL}"
            )
        _pause_for_menu()

    elif choice == "4":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('Exchange login  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}"
        )
        print()
        if not accs:
            print(f"{Style.DIM}{_center_plain_line('No linked accounts yet.', tw)}{Style.RESET_ALL}")
            _pause_for_menu()
            continue
        max_lab = max(12, tw - 18)
        inner = 36
        for i, a in enumerate(accs):
            lab = _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab)
            ph = (i * 2.0) % 12.0
            left_only = f"{_account_index_glyph(i, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
            inner = max(inner, _str_display_width(left_only) + 2)
        account_lines = [
            _account_list_row(
                i,
                _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab),
                inner,
                (i * 2.0) % 12.0,
                "",
            )
            for i, a in enumerate(accs)
        ]
        mw = max(_str_display_width(ln) for ln in account_lines)
        for ln in account_lines:
            print(" " * max(0, (tw - mw) // 2) + ln)
        print()
        print(f"{Style.DIM}{_center_plain_line('index 0–' + str(len(accs) - 1), tw)}{Style.RESET_ALL}")
        prompt_plain = "> "
        pad = max(0, (tw - _str_display_width(prompt_plain)) // 2)
        idx = input(" " * pad + f"{Style.DIM}>{Style.RESET_ALL} ").strip()
        if idx.isdigit() and 0 <= int(idx) < len(accs):
            acc = accs[int(idx)]
            try:
                rr = requests.post(
                    "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    headers={
                        "Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "device_auth",
                        "device_id": base64.b64decode(acc["deviceId"]).decode(),
                        "account_id": acc["accountId"],
                        "secret": base64.b64decode(acc["secret"]).decode(),
                    },
                    timeout=10,
                )
                if rr.status_code == 200:
                    tok = rr.json()["access_token"]
                    code = fetch_exchange_code(tok)
                    if code:
                        epic_url = epic_exchange_url(code)
                        print()
                        _print_rainbow_url(epic_url, tw)
                        print()
                        with open(os.devnull, "w") as dn:
                            _stderr_hold = sys.stderr
                            sys.stderr = dn
                            try:
                                webbrowser.open(epic_url)
                            finally:
                                sys.stderr = _stderr_hold
                    else:
                        print()
                        print(f"{Style.DIM}{_center_plain_line('No codes.', tw)}{Style.RESET_ALL}")
                        print()
                else:
                    print()
                    print(f"{Style.DIM}{_center_plain_line('Auth failed.', tw)}{Style.RESET_ALL}")
                    print()
            except Exception:
                print()
                print(f"{Style.DIM}{_center_plain_line('Auth failed.', tw)}{Style.RESET_ALL}")
                print()
        else:
            print(f"{Style.DIM}{_center_plain_line('0–' + str(len(accs) - 1) + ' only', tw)}{Style.RESET_ALL}")
        _pause_for_menu()

    elif choice == "5":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(f"{Style.DIM}{_center_plain_line('Gift item  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}")
        print()
        if not accs:
            _gift_note("No linked accounts yet.")
            _pause_for_menu()
            continue
        gift_menu_rows = [
            f"{_bracket_glyph('1', 0.0)}{Style.DIM} > One gift{Style.RESET_ALL}",
            f"{_bracket_glyph('2', 2.0)}{Style.DIM} > Whole shop{Style.RESET_ALL}",
        ]
        for gr in gift_menu_rows:
            print(_GIFT_MARGIN + gr)
        print()
        _gift_note("Pick 1 or 2")
        sub = _gift_ask()

        if sub == "1":
            print()
            _gift_note("Shop link")
            url_in = _gift_ask()
            if not url_in:
                _gift_note("Paste a link.")
                _pause_for_menu()
                continue
            if not _is_fortnite_shop_url(url_in):
                _gift_note("Bad link.")
                _pause_for_menu()
                continue
            slug = _item_slug_from_shop_url(url_in)
            if not slug:
                _gift_note("No item id.")
                _pause_for_menu()
                continue
            _gift_note("Recipient")
            username = _gift_ask()
            if not username:
                _gift_note("Need a name.")
                _pause_for_menu()
                continue
            _gift_note("Loading…")
            try:
                shop = requests.get("https://fortnite-api.com/v2/shop", timeout=15).json().get("data", {}).get("entries", [])
            except Exception:
                shop = []
            entry, disp_name = None, None
            target = slug
            target_words = [w for w in target.split("-") if w]
            for e in shop:
                ly = e.get("layout") or {}
                nm_ly = (ly.get("name") or "").lower()
                if e.get("tracks") or ("jam" in nm_ly and "track" in nm_ly) or (ly.get("id") or "").upper().startswith("JT"):
                    continue
                nm = _best_entry_display_name(e)
                nm_slug = _slugify_name(nm)
                if not nm_slug:
                    continue
                if nm_slug == target or target in nm_slug:
                    entry, disp_name = e, nm
                    break
            if not entry and target_words:
                for e in shop:
                    nm = _best_entry_display_name(e)
                    nm_slug = _slugify_name(nm)
                    if nm_slug and all(w in nm_slug for w in target_words):
                        entry, disp_name = e, nm
                        break
            if not entry:
                _gift_note("Not in shop.")
                _pause_for_menu()
                continue
            offer_id = entry.get("offerId")
            price = entry.get("finalPrice") or entry.get("regularPrice") or 0
            name = disp_name or _best_entry_display_name(entry) or ""
            cat = _shop_category_label(url_in)
            bits: list[str] = []
            if cat:
                bits.append(cat)
            bits.append(name)
            bits.append(f"{price} VB")
            print()
            _gift_note(" · ".join(bits))
            print()
            try:
                tok = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "device_auth", "device_id": base64.b64decode(accs[0]["deviceId"]).decode(), "account_id": accs[0]["accountId"], "secret": base64.b64decode(accs[0]["secret"]).decode()}, timeout=10).json().get("access_token")
            except Exception:
                tok = None
            recipient_id = username if len(username) == 32 and all(c in "0123456789abcdef" for c in username.lower()) else None
            if not recipient_id and tok:
                try:
                    rrr = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{username}", headers={"Authorization": "Bearer " + tok}, timeout=10)
                    if rrr.status_code == 200:
                        recipient_id = rrr.json().get("id")
                except Exception:
                    pass
            if not recipient_id:
                _gift_note("Not found.")
                _pause_for_menu()
                continue
            max_lb = max(12, tw - 18)
            inner_b = 36
            for i, a in enumerate(accs):
                lab = _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lb)
                ph = (i * 2.0) % 12.0
                left_only = f"{_account_index_glyph(i, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
                inner_b = max(inner_b, _str_display_width(left_only) + 2)
            bot_rows = [
                _account_list_row(
                    i,
                    _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lb),
                    inner_b,
                    (i * 2.0) % 12.0,
                    "",
                )
                for i, a in enumerate(accs)
            ]
            _gift_note("Accounts")
            for ln in bot_rows:
                print(_GIFT_MARGIN + ln)
            print()
            _gift_note("Bot # · Enter = all")
            bot_pick = _gift_ask().lower()
            if bot_pick.isdigit() and 0 <= int(bot_pick) < len(accs):
                bot_order = [int(bot_pick)]
            else:
                bot_order = list(range(len(accs)))
            sent, skip = False, False
            for bi in bot_order:
                bot = accs[bi]
                print()
                _gift_note(
                    _truncate_visible(
                        f"{bi + 1} · " + (bot.get("displayName") or bot["accountId"][:12]),
                        max(12, tw - 6),
                    )
                )
                try:
                    bt = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                        headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                        data={"grant_type": "device_auth", "device_id": base64.b64decode(bot["deviceId"]).decode(), "account_id": bot["accountId"], "secret": base64.b64decode(bot["secret"]).decode()}, timeout=10).json().get("access_token")
                    if not bt:
                        continue
                    rpost = requests.post(f"https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/{bot['accountId']}/client/GiftCatalogEntry?profileId=common_core",
                        json={"offerId": offer_id, "currency": "MtxCurrency", "currencySubType": "", "expectedTotalPrice": price, "gameContext": "Frontend.CatabaScreen", "receiverAccountIds": [recipient_id], "giftWrapTemplateId": "", "personalMessage": ""},
                        headers={"Authorization": "Bearer " + bt}, timeout=5)
                    txt = (rpost.text or "").lower()
                    if rpost.status_code == 200 and "profilechanges" in txt and "errors.com.epicgames" not in txt:
                        _gift_note("Gift sent.")
                        sent = True
                        break
                    if "user already owns" in txt or "all items in this bundle are already owned" in txt or "invalid_parameter" in txt or "receiver_owns_item" in txt:
                        _gift_note("Skipped.")
                        skip = True
                        break
                except Exception:
                    pass
            if not sent and not skip:
                _gift_note("Failed.")
            _pause_for_menu()

        elif sub == "2":
            print()
            _gift_note("Recipient")
            username = _gift_ask()
            if not username:
                _gift_note("Need a name.")
                _pause_for_menu()
                continue
            _gift_note("Loading…")
            try:
                shop = requests.get("https://fortnite-api.com/v2/shop", timeout=15).json().get("data", {}).get("entries", [])
            except Exception:
                shop = []
            giftable = []
            for e in shop:
                ly = e.get("layout") or {}
                nm_ly = (ly.get("name") or "").lower()
                if e.get("tracks") or ("jam" in nm_ly and "track" in nm_ly) or (ly.get("id") or "").upper().startswith("JT"):
                    continue
                if (e.get("finalPrice") or 0) > 0 and e.get("giftable", True):
                    giftable.append(e)
            print()
            _gift_note(f"{len(giftable)} giftable items")
            print()
            try:
                tok = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "device_auth", "device_id": base64.b64decode(accs[0]["deviceId"]).decode(), "account_id": accs[0]["accountId"], "secret": base64.b64decode(accs[0]["secret"]).decode()}, timeout=10).json().get("access_token")
            except Exception:
                tok = None
            recipient_id = username if len(username) == 32 and all(c in "0123456789abcdef" for c in username.lower()) else None
            if not recipient_id and tok:
                try:
                    rrr = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{username}", headers={"Authorization": "Bearer " + tok}, timeout=10)
                    if rrr.status_code == 200:
                        recipient_id = rrr.json().get("id")
                except Exception:
                    pass
            if not recipient_id:
                _gift_note("Not found.")
                _pause_for_menu()
                continue
            bot_idx, sent_count, skipped_count = 0, 0, 0
            for i, entry in enumerate(giftable):
                offer_id = entry.get("offerId")
                price = entry.get("finalPrice") or entry.get("regularPrice") or 0
                nm = _best_entry_display_name(entry)
                if not offer_id or price <= 0:
                    continue
                while bot_idx < len(accs):
                    bot = accs[bot_idx]
                    print()
                    _gift_note(
                        _truncate_visible(
                            f"{i + 1}/{len(giftable)} · {nm} · {price} VB",
                            max(12, tw - 6),
                        )
                    )
                    try:
                        bt = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                            headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                            data={"grant_type": "device_auth", "device_id": base64.b64decode(bot["deviceId"]).decode(), "account_id": bot["accountId"], "secret": base64.b64decode(bot["secret"]).decode()}, timeout=10).json().get("access_token")
                        if not bt:
                            bot_idx += 1
                            continue
                        rpost = requests.post(f"https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/{bot['accountId']}/client/GiftCatalogEntry?profileId=common_core",
                            json={"offerId": offer_id, "currency": "MtxCurrency", "currencySubType": "", "expectedTotalPrice": price, "gameContext": "Frontend.CatabaScreen", "receiverAccountIds": [recipient_id], "giftWrapTemplateId": "", "personalMessage": ""},
                            headers={"Authorization": "Bearer " + bt}, timeout=5)
                        txt = (rpost.text or "").lower()
                        if rpost.status_code == 200 and "profilechanges" in txt and "errors.com.epicgames" not in txt:
                            _gift_note("Gift sent.")
                            sent_count += 1
                            break
                        if "user already owns" in txt or "all items in this bundle are already owned" in txt or "invalid_parameter" in txt or "receiver_owns_item" in txt:
                            _gift_note("Skipped.")
                            skipped_count += 1
                            break
                        bot_idx += 1
                        if bot_idx >= len(accs):
                            _gift_note("No bots left.")
                            break
                    except Exception:
                        bot_idx += 1
                if bot_idx >= len(accs):
                    break
                time.sleep(5)
            print()
            _gift_note(f"{sent_count} sent · {skipped_count} skip")
            _pause_for_menu()

        else:
            _gift_note("Choose 1 or 2.")
            _pause_for_menu()

    elif choice == "6":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except Exception:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except Exception:
                accs = []
        tw = _term_cols()
        print(_rainbow_separator_line(tw) + Style.RESET_ALL)
        print()
        print(
            f"{Style.DIM}{_center_plain_line('Quick launch Fortnite  ·  ' + str(len(accs)) + ' saved', tw)}{Style.RESET_ALL}"
        )
        print()
        if not accs:
            _gift_note("No linked accounts yet.")
            _pause_for_menu()
            continue

        max_lab = max(12, tw - 18)
        inner = 36
        for i, a in enumerate(accs):
            lab = _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab)
            ph = (i * 2.0) % 12.0
            left_only = f"{_account_index_glyph(i, ph)}{Style.DIM} > {lab}{Style.RESET_ALL}"
            inner = max(inner, _str_display_width(left_only) + 2)
        account_lines = [
            _account_list_row(
                i,
                _truncate_visible(a.get("displayName") or (a["accountId"][:14] + "…"), max_lab),
                inner,
                (i * 2.0) % 12.0,
                "",
            )
            for i, a in enumerate(accs)
        ]
        print()
        for ln in account_lines:
            print(_GIFT_MARGIN + ln)
        print()
        _gift_note(f"Account 0–{len(accs) - 1}")
        idx = _gift_ask().strip()
        if not idx.isdigit() or not (0 <= int(idx) < len(accs)):
            _gift_note(f"Use 0–{len(accs) - 1}.")
            _pause_for_menu()
            continue

        acc = accs[int(idx)]
        epic_id = acc.get("accountId") or ""
        if not epic_id:
            _gift_note("Account has no accountId.")
            _pause_for_menu()
            continue

        try:
            rr = requests.post(
                "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={
                    "Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "device_auth",
                    "device_id": base64.b64decode(acc["deviceId"]).decode(),
                    "account_id": acc["accountId"],
                    "secret": base64.b64decode(acc["secret"]).decode(),
                },
                timeout=10,
            )
            if rr.status_code != 200:
                print()
                _gift_note("Auth failed.")
                print()
                _pause_for_menu()
                continue
            tok = rr.json().get("access_token")
            if not tok:
                print()
                _gift_note("Auth failed.")
                print()
                _pause_for_menu()
                continue
            code = fetch_exchange_code(tok)
            if not code:
                print()
                _gift_note("No codes.")
                print()
                _pause_for_menu()
                continue

            launch_cmd = _fortnite_exchange_launch_cmd(code, epic_id)
            print()
            if platform.system() != "Windows":
                _gift_note("Windows only. Run this in cmd.exe:")
                _gift_note(launch_cmd)
                print()
                _pause_for_menu()
                continue

            _gift_note("Starting Fortnite (Win64)…")
            try:
                subprocess.Popen(launch_cmd, shell=True, close_fds=True)
            except Exception as e:
                _gift_note(f"Could not start: {e}")
                _gift_note("Copy into cmd:")
                _gift_note(launch_cmd)
            print()
        except Exception:
            print()
            _gift_note("Auth failed.")
            print()
        _pause_for_menu()

    elif choice == "0":
        break
