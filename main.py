#!/usr/bin/env python3

import os
import sys
import re
import json
import time
import base64
import webbrowser
import requests
import contextlib
from colorama import Fore, Style, init
import fade

FORTNITE_API_SHOP = "https://fortnite-api.com/v2/shop"
GIFT_TIMEOUT = 5
GIFT_DELAY_PER_ITEM = 5

# =======================
# INIT / STYLE
# =======================

init(autoreset=True)
PURPLE = Fore.MAGENTA
RESET = Style.RESET_ALL
VERSION = "1.0.5"

def clear():
    try:
        print("\033[2J\033[H", end="", flush=True)
    except Exception:
        try:
            os.system("cls" if os.name == "nt" else "clear")
        except Exception:
            pass

@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old

# =======================
# CONFIG
# =======================

CONFIG_PATH = "config.json"

EPIC_BASE = "https://account-public-service-prod.ol.epicgames.com"
CLIENT_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
DEVICE_CLIENT_TOKEN = "M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU="

# =======================
# UI
# =======================

def banner():
    clear()
    print(
        PURPLE + fade.purplepink(f"""
                                                d8P                         
                                             d888888P                       
           88bd8b,d88b  d8888b ?88   d8P  d8P  ?88'   ?88   d8P  d8P d8888b 
           88P'`?8P'?8bd8b_,dP d88  d8P' d8P'  88P    d88  d8P' d8P'd8P' ?88
          d88  d88  88P88b     ?8b ,88b ,88'   88b    ?8b ,88b ,88' 88b  d88
         d88' d88'  88b`?888P' `?888P'888P'    `?8b   `?888P'888P'  `?8888P'

                                                            V{VERSION}
        """) + RESET
    )

def pause():
    input("\nPress ENTER to continue...")

def log(msg):
    print(f"    [{PURPLE}!{RESET}] {msg}")

# =======================
# STORAGE
# =======================

def load_accounts():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_account(account):
    accounts = load_accounts()
    if any(a["accountId"] == account["accountId"] for a in accounts):
        return False
    accounts.append(account)
    with open(CONFIG_PATH, "w") as f:
        json.dump(accounts, f, indent=4)
    return True

# =======================
# ACCOUNT INFO
# =======================

def get_token_for_account(account):
    try:
        device_id = base64.b64decode(account["deviceId"]).decode()
        secret = base64.b64decode(account["secret"]).decode()
        account_id = account["accountId"]
    except Exception:
        return None
    r = requests.post(
        f"{EPIC_BASE}/account/api/oauth/token",
        headers={
            "Authorization": f"Basic {DEVICE_CLIENT_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "device_auth",
            "device_id": device_id,
            "account_id": account_id,
            "secret": secret,
        },
        timeout=10,
    )
    if r.status_code != 200:
        return None
    data = r.json()
    return data.get("access_token")

def fetch_account_info(account):
    token = get_token_for_account(account)
    if not token:
        return None, None
    r = requests.get(
        f"{EPIC_BASE}/account/api/public/account/{account['accountId']}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if r.status_code != 200:
        return None, None
    data = r.json()
    display_name = data.get("displayName") or data.get("name") or "Unknown"
    email = data.get("email") or "N/A"
    return display_name, email

def get_account_id_from_username(username, access_token):
    if not username or not access_token:
        return None
    if len(username) == 32 and all(c in "0123456789abcdef" for c in username.lower()):
        return username
    try:
        r = requests.get(
            f"{EPIC_BASE}/account/api/public/account/displayName/{username}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("id")
    except Exception:
        pass
    return None

def fetch_shop_entries():
    try:
        r = requests.get(FORTNITE_API_SHOP, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        entries = data.get("data", {}).get("entries", [])
        return entries
    except Exception:
        return []

def extract_item_slug_from_url(url):
    if not url or not isinstance(url, str):
        return None
    m = re.search(r"/item-shop/[^/]+/([^/?\-]+)", url)
    if m:
        return m.group(1).lower()
    m = re.search(r"/([a-zA-Z0-9]+)-[a-f0-9]{8}", url)
    if m:
        return m.group(1).lower()
    return None

def find_shop_item_by_slug(entries, slug):
    slug = (slug or "").lower()
    if not slug:
        return None, None
    for e in entries:
        if is_jam_track(e):
            continue
        name = _get_entry_display_name(e)
        if slug in (name or "").lower():
            return e, name
    return None, None

def is_jam_track(entry):
    """Return True if entry is a Jam Track (skip when gifting entire shop)."""
    if entry.get("tracks"):
        return True
    layout = entry.get("layout") or {}
    name = (layout.get("name") or "").lower()
    if "jam" in name and "track" in name:
        return True
    lid = (layout.get("id") or "").upper()
    if lid.startswith("JT"):
        return True
    return False

def _get_entry_display_name(entry):
    """Get human-readable name from shop entry."""
    br = entry.get("brItems") or []
    if br:
        return br[0].get("name") or ""
    bundle = entry.get("bundle") or {}
    if bundle.get("name"):
        return bundle["name"]
    dev = entry.get("devName") or ""
    m = re.search(r"\d+\s*x\s+([^f]+?)\s+for\s+\d+", dev, re.I)
    if m:
        return m.group(1).strip()
    return dev

def attempt_gift(bot_account, recipient_account_id, offer_id, price, item_name, timeout=GIFT_TIMEOUT):
    """
    Attempt to send a gift. Returns (success: bool, rotate_bot: bool, skip_item: bool).
    - success: gift sent
    - rotate_bot: try next bot (gift limit or no vbucks)
    - skip_item: skip this item, try next with same bot (owns bundle, invalid_parameter)
    """
    token = get_token_for_account(bot_account)
    if not token:
        return False, True, False
    try:
        device_id = base64.b64decode(bot_account["deviceId"]).decode()
        account_id = bot_account["accountId"]
    except Exception:
        return False, True, False
    gift_url = f"https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/{account_id}/client/GiftCatalogEntry?profileId=common_core"
    payload = {
        "offerId": offer_id,
        "currency": "MtxCurrency",
        "currencySubType": "",
        "expectedTotalPrice": price,
        "gameContext": "Frontend.CatabaScreen",
        "receiverAccountIds": [recipient_account_id],
        "giftWrapTemplateId": "",
        "personalMessage": "",
    }
    try:
        r = requests.post(
            gift_url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        text = (r.text or "").lower()
        if r.status_code == 200 and "profilechanges" in text and "errors.com.epicgames" not in text:
            return True, False, False
        if "user already owns items from this bundle" in text:
            return False, False, True
        if "all items in this bundle are already owned" in text:
            return False, False, True
        if "errors.com.epicgames.modules.gamesubcatalog.invalid_parameter" in text:
            return False, False, True
        if "errors.com.epicgames.modules.gamesubcatalog.receiver_owns_item_from_bundle" in text:
            return False, False, True
        if "errors.com.epicgames.modules.gamesubcatalog.gift_limit_reached" in text:
            return False, True, False
        if "insufficient" in text or "gift_limit" in text or "vbucks" in text or "currency" in text:
            return False, True, False
        return False, True, False
    except requests.exceptions.Timeout:
        return False, True, False
    except Exception:
        return False, True, False

# =======================
# AUTH FLOW
# =======================

def initiate_device_auth():
    r = requests.post(
        f"{EPIC_BASE}/account/api/oauth/token",
        headers={
            "Authorization": f"Basic {CLIENT_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
    ).json()

    token = r["access_token"]

    return requests.post(
        f"{EPIC_BASE}/account/api/oauth/deviceAuthorization",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

def poll_for_login(device_code):
    while True:
        time.sleep(11)
        r = requests.post(
            f"{EPIC_BASE}/account/api/oauth/token",
            headers={
                "Authorization": f"Basic {CLIENT_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "device_code",
                "device_code": device_code,
            },
        )
        if r.status_code != 400:
            data = r.json()
            return data["account_id"], data["access_token"]

def create_device_auth(account_id, access_token):
    exchange = requests.get(
        f"{EPIC_BASE}/account/api/oauth/exchange",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()["code"]

    token = requests.post(
        f"{EPIC_BASE}/account/api/oauth/token",
        headers={
            "Authorization": f"Basic {DEVICE_CLIENT_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "exchange_code",
            "exchange_code": exchange,
        },
    ).json()["access_token"]

    device = requests.post(
        f"{EPIC_BASE}/account/api/public/account/{account_id}/deviceAuth",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    return {
        "accountId": account_id,
        "deviceId": base64.b64encode(device["deviceId"].encode()).decode(),
        "secret": base64.b64encode(device["secret"].encode()).decode(),
    }

# =======================
# MENU
# =======================

def show_menu():
    print(f"{PURPLE}Menu{RESET}")
    print(f"{PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  [{PURPLE}1{RESET}] Add Epic account")
    print(f"  [{PURPLE}2{RESET}] View linked accounts")
    print(f"  [{PURPLE}3{RESET}] Remove account")
    print(f"  [{PURPLE}4{RESET}] Generate exchange code")
    print(f"  [{PURPLE}5{RESET}] Gift item")
    print(f"  [{PURPLE}6{RESET}] Gift entire shop")
    print(f"  [{PURPLE}0{RESET}] Exit\n")
    return input("Choice: ").strip()

# =======================
# MAIN LOOP
# =======================

def main():
    while True:
        banner()
        choice = show_menu()

        if choice == "1":
            banner()
            log("Starting Epic Device Authentication")

            auth = initiate_device_auth()
            with suppress_stderr():
                webbrowser.open(auth["verification_uri_complete"])

            account_id, access_token = poll_for_login(auth["device_code"])
            log(f"Authenticated account {account_id}")

            device_auth = create_device_auth(account_id, access_token)
            try:
                r = requests.get(
                    f"{EPIC_BASE}/account/api/public/account/{account_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()
                    device_auth["displayName"] = data.get("displayName") or data.get("name") or "Unknown"
            except Exception:
                pass
            saved = save_account(device_auth)
            log("Account saved" if saved else "Account already exists")
            pause()

        elif choice == "2":
            banner()
            accounts = load_accounts()
            log(f"Linked accounts: {len(accounts)}")
            for a in accounts:
                display_name, email = fetch_account_info(a)
                if display_name is None:
                    display_name, email = "?", "N/A"
                print(f"    {display_name}")
                print(f"      {email}")
                print(f"      ({a['accountId']})")
                print()
                time.sleep(0.2)
            pause()

        elif choice == "3":
            banner()
            accounts = load_accounts()
            for i, a in enumerate(accounts):
                disp = a.get("displayName") or a["accountId"][:12] + "..."
                print(f"  [{i}] {disp} ({a['accountId']})")
            idx = input("\nIndex to remove: ").strip()
            if idx.isdigit() and int(idx) < len(accounts):
                accounts.pop(int(idx))
                with open(CONFIG_PATH, "w") as f:
                    json.dump(accounts, f, indent=4)
                log("Account removed")
            pause()

        elif choice == "4":
            banner()
            accounts = load_accounts()
            if not accounts:
                log("No accounts")
            else:
                for i, a in enumerate(accounts):
                    disp = a.get("displayName") or a["accountId"][:12]
                    print(f"  [{i}] {disp} ({a['accountId']})")
                idx = input("\nIndex: ").strip()
                if idx.isdigit() and int(idx) < len(accounts):
                    acc = accounts[int(idx)]
                    token = get_token_for_account(acc)
                    if token:
                        r = requests.get(
                            f"{EPIC_BASE}/account/api/oauth/exchange",
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        if r.status_code == 200:
                            code = r.json().get("code")
                            log(f"Exchange code: {code}")
                            log("Login link: " + f"https://www.epicgames.com/id/exchange?exchangeCode={code}")
                        else:
                            log("Failed to get exchange code")
                    else:
                        log("Invalid device auth")
            pause()

        elif choice == "5":
            banner()
            accounts = load_accounts()
            if not accounts:
                log("No bot accounts linked. Add accounts first.")
                pause()
                continue
            print(f"  {PURPLE}Gift Item{RESET}")
            print(f"  {PURPLE}─────────{RESET}\n")
            url_input = input("  Item shop URL (e.g. fortnite.com/item-shop/emotes/...): ").strip()
            slug = extract_item_slug_from_url(url_input) if url_input else None
            if not slug:
                slug = input("  Or enter item name (e.g. femininomenon): ").strip().lower()
            if not slug:
                log("No item specified")
                pause()
                continue
            username = input("  Recipient username: ").strip()
            if not username:
                log("No recipient specified")
                pause()
                continue
            log("Fetching shop...")
            entries = fetch_shop_entries()
            entry, disp_name = find_shop_item_by_slug(entries, slug)
            if not entry:
                log(f"Item not found in shop: {slug}")
                pause()
                continue
            offer_id = entry.get("offerId")
            price = entry.get("finalPrice", entry.get("regularPrice", 0))
            name = disp_name or _get_entry_display_name(entry)
            log(f"Found: {name} ({price} V-Bucks)")
            token = get_token_for_account(accounts[0])
            recipient_id = get_account_id_from_username(username, token)
            if not recipient_id:
                log("Could not resolve username to account ID")
                pause()
                continue
            log(f"Recipient: {username} -> {recipient_id}")
            bot_idx = 0
            sent = False
            while bot_idx < len(accounts):
                bot = accounts[bot_idx]
                disp = bot.get("displayName") or bot["accountId"][:12]
                print(f"\n  [{PURPLE}Bot{bot_idx + 1}{RESET}] Trying {disp} ({bot['accountId'][:8]}...)")
                success, rotate, skip = attempt_gift(bot, recipient_id, offer_id, price, name)
                if success:
                    log(f"  {PURPLE}SUCCESS{RESET} - {name} sent!")
                    sent = True
                    break
                if skip:
                    log(f"  Skipped (recipient owns / item not giftable)")
                    break
                if rotate:
                    log(f"  Rotating to next bot...")
                    bot_idx += 1
                else:
                    break
            if not sent and not skip:
                log("All bots failed (limit/vbucks)")
            pause()

        elif choice == "6":
            banner()
            accounts = load_accounts()
            if not accounts:
                log("No bot accounts linked. Add accounts first.")
                pause()
                continue
            print(f"  {PURPLE}Gift Entire Shop{RESET}")
            print(f"  {PURPLE}───────────────{RESET}\n")
            log("Jam Tracks will be skipped.")
            username = input("  Recipient username: ").strip()
            if not username:
                log("No recipient specified")
                pause()
                continue
            log("Fetching shop...")
            entries = fetch_shop_entries()
            giftable = [e for e in entries if not is_jam_track(e) and (e.get("finalPrice") or 0) > 0 and e.get("giftable", True)]
            log(f"Found {len(giftable)} giftable items (excluding Jam Tracks)")
            token = get_token_for_account(accounts[0])
            recipient_id = get_account_id_from_username(username, token)
            if not recipient_id:
                log("Could not resolve username to account ID")
                pause()
                continue
            log(f"Recipient: {username} -> {recipient_id}")
            bot_idx = 0
            sent_count = 0
            skipped_count = 0
            for i, entry in enumerate(giftable):
                offer_id = entry.get("offerId")
                price = entry.get("finalPrice") or entry.get("regularPrice", 0)
                name = _get_entry_display_name(entry)
                if not offer_id or price <= 0:
                    continue
                while bot_idx < len(accounts):
                    bot = accounts[bot_idx]
                    disp = bot.get("displayName") or bot["accountId"][:12]
                    print(f"\n  [{i+1}/{len(giftable)}] {name} ({price} VB) - Bot: {disp}")
                    success, rotate, skip = attempt_gift(bot, recipient_id, offer_id, price, name)
                    if success:
                        log(f"  {PURPLE}SUCCESS{RESET}")
                        sent_count += 1
                        break
                    if skip:
                        log(f"  Skipped (owns / not giftable)")
                        skipped_count += 1
                        break
                    if rotate:
                        bot_idx += 1
                        if bot_idx >= len(accounts):
                            log(f"  No more bots. Stopping.")
                            break
                if bot_idx >= len(accounts):
                    break
                time.sleep(GIFT_DELAY_PER_ITEM)
            log(f"\n  Done. Sent: {sent_count} | Skipped: {skipped_count}")
            pause()

        elif choice == "0":
            break

if __name__ == "__main__":
    main()
