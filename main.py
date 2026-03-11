#!/usr/bin/env python3

'''
/----------------------🪐-----------------------\
     Made & Developed by @calebdev on tele
/------------------------------------------------\
'''

import os, sys, re, json, time, base64, webbrowser, requests
from colorama import Fore, Style, init
import fade

init(autoreset=True)

while True:
    try:
        print("\033[2J\033[H", end="", flush=True)
    except:
        try:
            os.system("cls" if os.name == "nt" else "clear")
        except:
            pass

    print(Fore.MAGENTA + fade.purplepink("""
                                                d8P                         
                                             d888888P                       
           88bd8b,d88b  d8888b ?88   d8P  d8P  ?88'   ?88   d8P  d8P d8888b 
           88P'`?8P'?8bd8b_,dP d88  d8P' d8P'  88P    d88  d8P' d8P'd8P' ?88
          d88  d88  88P88b     ?8b ,88b ,88'   88b    ?8b ,88b ,88' 88b  d88
         d88' d88'  88b`?888P' `?888P'888P'    `?8b   `?888P'888P'  `?8888P'

                                                            V1.0.5
    """) + Style.RESET_ALL)

    print(f"{Fore.MAGENTA}Menu{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
    print(f"  [{Fore.MAGENTA}1{Style.RESET_ALL}] Add Epic account")
    print(f"  [{Fore.MAGENTA}2{Style.RESET_ALL}] View linked accounts")
    print(f"  [{Fore.MAGENTA}3{Style.RESET_ALL}] Remove account")
    print(f"  [{Fore.MAGENTA}4{Style.RESET_ALL}] Generate exchange code")
    print(f"  [{Fore.MAGENTA}5{Style.RESET_ALL}] Gift item")
    print(f"  [{Fore.MAGENTA}6{Style.RESET_ALL}] Gift entire shop")
    print(f"  [{Fore.MAGENTA}0{Style.RESET_ALL}] Exit\n")
    choice = input("Choice: ").strip()

    if choice == "1":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Starting Epic Device Authentication")
        r = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            headers={"Authorization": "Basic OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"}).json()
        auth = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/deviceAuthorization", headers={"Authorization": "Bearer " + r["access_token"]}).json()
        with open(os.devnull, "w") as dn:
            _ = sys.stderr
            sys.stderr = dn
            try:
                webbrowser.open(auth["verification_uri_complete"])
            finally:
                sys.stderr = _
        while True:
            time.sleep(11)
            resp = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={"Authorization": "Basic OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3", "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "device_code", "device_code": auth["device_code"]})
            if resp.status_code != 400:
                d = resp.json()
                account_id, access_token = d["account_id"], d["access_token"]
                break
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Authenticated account {account_id}")
        exch = requests.get("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/exchange", headers={"Authorization": "Bearer " + access_token}).json()["code"]
        tok = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "exchange_code", "exchange_code": exch}).json()["access_token"]
        dev = requests.post(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}/deviceAuth", headers={"Authorization": "Bearer " + tok}).json()
        device_auth = {"accountId": account_id, "deviceId": base64.b64encode(dev["deviceId"].encode()).decode(), "secret": base64.b64encode(dev["secret"].encode()).decode()}
        try:
            rr = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}", headers={"Authorization": "Bearer " + access_token}, timeout=10)
            if rr.status_code == 200:
                device_auth["displayName"] = rr.json().get("displayName") or rr.json().get("name") or "Unknown"
        except:
            pass
        accs = []
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    accs = json.load(f)
            except:
                accs = []
        if any(a["accountId"] == device_auth["accountId"] for a in accs):
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Account already exists")
        else:
            accs.append(device_auth)
            with open("config.json", "w") as f:
                json.dump(accs, f, indent=4)
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Account saved")
        input("\nPress ENTER to continue...")

    elif choice == "2":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        accs = json.load(open("config.json")) if os.path.exists("config.json") else []
        if not os.path.exists("config.json"):
            accs = []
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Linked accounts: {len(accs)}")
        for a in accs:
            display_name, email = "?", "N/A"
            try:
                did = base64.b64decode(a["deviceId"]).decode()
                sec = base64.b64decode(a["secret"]).decode()
                rr = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                    headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                    data={"grant_type": "device_auth", "device_id": did, "account_id": a["accountId"], "secret": sec}, timeout=10)
                if rr.status_code == 200:
                    tok = rr.json().get("access_token")
                    r2 = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{a['accountId']}", headers={"Authorization": "Bearer " + tok}, timeout=10)
                    if r2.status_code == 200:
                        dd = r2.json()
                        display_name = dd.get("displayName") or dd.get("name") or "Unknown"
                        email = dd.get("email") or "N/A"
            except:
                pass
            print(f"    {display_name}\n      {email}\n      ({a['accountId']})\n")
            time.sleep(0.2)
        input("\nPress ENTER to continue...")

    elif choice == "3":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        accs = json.load(open("config.json")) if os.path.exists("config.json") else []
        for i, a in enumerate(accs):
            print(f"  [{i}] {a.get('displayName') or a['accountId'][:12]+'...'} ({a['accountId']})")
        idx = input("\nIndex to remove: ").strip()
        if idx.isdigit() and int(idx) < len(accs):
            accs.pop(int(idx))
            with open("config.json", "w") as f:
                json.dump(accs, f, indent=4)
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Account removed")
        input("\nPress ENTER to continue...")

    elif choice == "4":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        accs = json.load(open("config.json")) if os.path.exists("config.json") else []
        if not accs:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No accounts")
        else:
            for i, a in enumerate(accs):
                print(f"  [{i}] {a.get('displayName') or a['accountId'][:12]} ({a['accountId']})")
            idx = input("\nIndex: ").strip()
            if idx.isdigit() and int(idx) < len(accs):
                acc = accs[int(idx)]
                try:
                    rr = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                        headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                        data={"grant_type": "device_auth", "device_id": base64.b64decode(acc["deviceId"]).decode(), "account_id": acc["accountId"], "secret": base64.b64decode(acc["secret"]).decode()}, timeout=10)
                    if rr.status_code == 200:
                        r2 = requests.get("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/exchange", headers={"Authorization": "Bearer " + rr.json()["access_token"]})
                        if r2.status_code == 200:
                            code = r2.json().get("code")
                            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Exchange code: {code}")
                            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Login link: https://www.epicgames.com/id/exchange?exchangeCode={code}")
                        else:
                            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Failed to get exchange code")
                    else:
                        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Invalid device auth")
                except:
                    print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Invalid device auth")
        input("\nPress ENTER to continue...")

    elif choice == "5":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        accs = json.load(open("config.json")) if os.path.exists("config.json") else []
        if not accs:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No bot accounts linked. Add accounts first.")
            input("\nPress ENTER to continue...")
            continue
        print(f"  {Fore.MAGENTA}Gift Item{Style.RESET_ALL}\n  {Fore.MAGENTA}─────────{Style.RESET_ALL}\n")
        url_in = input("  Item shop URL (e.g. fortnite.com/item-shop/emotes/...): ").strip()
        slug = None
        if url_in:
            m = re.search(r"/item-shop/[^/]+/([^/?\-]+)", url_in)
            slug = m.group(1).lower() if m else (re.search(r"/([a-zA-Z0-9]+)-[a-f0-9]{8}", url_in).group(1).lower() if re.search(r"/([a-zA-Z0-9]+)-[a-f0-9]{8}", url_in) else None)
        if not slug:
            slug = input("  Or enter item name (e.g. femininomenon): ").strip().lower()
        if not slug:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No item specified")
            input("\nPress ENTER to continue...")
            continue
        username = input("  Recipient username: ").strip()
        if not username:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No recipient specified")
            input("\nPress ENTER to continue...")
            continue
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Fetching shop...")
        try:
            shop = requests.get("https://fortnite-api.com/v2/shop", timeout=15).json().get("data", {}).get("entries", [])
        except:
            shop = []
        entry, disp_name = None, None
        for e in shop:
            ly = e.get("layout") or {}
            nm_ly = (ly.get("name") or "").lower()
            if e.get("tracks") or ("jam" in nm_ly and "track" in nm_ly) or (ly.get("id") or "").upper().startswith("JT"):
                continue
            br = e.get("brItems") or []
            nm = br[0].get("name") if br else (e.get("bundle") or {}).get("name") or ""
            if not nm:
                m2 = re.search(r"\d+\s*x\s+([^f]+?)\s+for\s+\d+", (e.get("devName") or ""), re.I)
                nm = m2.group(1).strip() if m2 else (e.get("devName") or "")
            if slug in (nm or "").lower():
                entry, disp_name = e, nm
                break
        if not entry:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Item not found in shop: {slug}")
            input("\nPress ENTER to continue...")
            continue
        offer_id = entry.get("offerId")
        price = entry.get("finalPrice") or entry.get("regularPrice") or 0
        name = disp_name or (entry.get("brItems") or [{}])[0].get("name") or (entry.get("bundle") or {}).get("name") or ""
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Found: {name} ({price} V-Bucks)")
        try:
            tok = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "device_auth", "device_id": base64.b64decode(accs[0]["deviceId"]).decode(), "account_id": accs[0]["accountId"], "secret": base64.b64decode(accs[0]["secret"]).decode()}, timeout=10).json().get("access_token")
        except:
            tok = None
        recipient_id = username if len(username) == 32 and all(c in "0123456789abcdef" for c in username.lower()) else None
        if not recipient_id and tok:
            try:
                rrr = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{username}", headers={"Authorization": "Bearer " + tok}, timeout=10)
                if rrr.status_code == 200:
                    recipient_id = rrr.json().get("id")
            except:
                pass
        if not recipient_id:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Could not resolve username to account ID")
            input("\nPress ENTER to continue...")
            continue
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Recipient: {username} -> {recipient_id}")
        bot_idx, sent, skip = 0, False, False
        while bot_idx < len(accs):
            bot = accs[bot_idx]
            print(f"\n  [{Fore.MAGENTA}Bot{bot_idx+1}{Style.RESET_ALL}] Trying {bot.get('displayName') or bot['accountId'][:12]} ({bot['accountId'][:8]}...)")
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
                    print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}]   {Fore.MAGENTA}SUCCESS{Style.RESET_ALL} - {name} sent!")
                    sent = True
                    break
                if "user already owns" in txt or "all items in this bundle are already owned" in txt or "invalid_parameter" in txt or "receiver_owns_item" in txt:
                    print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}]   Skipped (recipient owns / item not giftable)")
                    skip = True
                    break
                bot_idx += 1
            except:
                bot_idx += 1
        if not sent and not skip:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] All bots failed (limit/vbucks)")
        input("\nPress ENTER to continue...")

    elif choice == "6":
        try:
            print("\033[2J\033[H", end="", flush=True)
        except:
            pass
        accs = json.load(open("config.json")) if os.path.exists("config.json") else []
        if not accs:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No bot accounts linked. Add accounts first.")
            input("\nPress ENTER to continue...")
            continue
        print(f"  {Fore.MAGENTA}Gift Entire Shop{Style.RESET_ALL}\n  {Fore.MAGENTA}───────────────{Style.RESET_ALL}\n")
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Jam Tracks will be skipped.")
        username = input("  Recipient username: ").strip()
        if not username:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] No recipient specified")
            input("\nPress ENTER to continue...")
            continue
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Fetching shop...")
        try:
            shop = requests.get("https://fortnite-api.com/v2/shop", timeout=15).json().get("data", {}).get("entries", [])
        except:
            shop = []
        giftable = []
        for e in shop:
            ly = e.get("layout") or {}
            nm_ly = (ly.get("name") or "").lower()
            if e.get("tracks") or ("jam" in nm_ly and "track" in nm_ly) or (ly.get("id") or "").upper().startswith("JT"):
                continue
            if (e.get("finalPrice") or 0) > 0 and e.get("giftable", True):
                giftable.append(e)
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Found {len(giftable)} giftable items (excluding Jam Tracks)")
        try:
            tok = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
                headers={"Authorization": "Basic M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU=", "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "device_auth", "device_id": base64.b64decode(accs[0]["deviceId"]).decode(), "account_id": accs[0]["accountId"], "secret": base64.b64decode(accs[0]["secret"]).decode()}, timeout=10).json().get("access_token")
        except:
            tok = None
        recipient_id = username if len(username) == 32 and all(c in "0123456789abcdef" for c in username.lower()) else None
        if not recipient_id and tok:
            try:
                rrr = requests.get(f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{username}", headers={"Authorization": "Bearer " + tok}, timeout=10)
                if rrr.status_code == 200:
                    recipient_id = rrr.json().get("id")
            except:
                pass
        if not recipient_id:
            print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Could not resolve username to account ID")
            input("\nPress ENTER to continue...")
            continue
        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}] Recipient: {username} -> {recipient_id}")
        bot_idx, sent_count, skipped_count = 0, 0, 0
        for i, entry in enumerate(giftable):
            offer_id = entry.get("offerId")
            price = entry.get("finalPrice") or entry.get("regularPrice") or 0
            br = entry.get("brItems") or []
            nm = br[0].get("name") if br else (entry.get("bundle") or {}).get("name") or ""
            if not nm:
                m2 = re.search(r"\d+\s*x\s+([^f]+?)\s+for\s+\d+", (entry.get("devName") or ""), re.I)
                nm = m2.group(1).strip() if m2 else (entry.get("devName") or "")
            if not offer_id or price <= 0:
                continue
            while bot_idx < len(accs):
                bot = accs[bot_idx]
                print(f"\n  [{i+1}/{len(giftable)}] {nm} ({price} VB) - Bot: {bot.get('displayName') or bot['accountId'][:12]}")
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
                        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}]   {Fore.MAGENTA}SUCCESS{Style.RESET_ALL}")
                        sent_count += 1
                        break
                    if "user already owns" in txt or "all items in this bundle are already owned" in txt or "invalid_parameter" in txt or "receiver_owns_item" in txt:
                        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}]   Skipped (owns / not giftable)")
                        skipped_count += 1
                        break
                    bot_idx += 1
                    if bot_idx >= len(accs):
                        print(f"    [{Fore.MAGENTA}!{Style.RESET_ALL}]   No more bots. Stopping.")
                        break
                except:
                    bot_idx += 1
            if bot_idx >= len(accs):
                break
            time.sleep(5)
        print(f"\n    [{Fore.MAGENTA}!{Style.RESET_ALL}] Done. Sent: {sent_count} | Skipped: {skipped_count}")
        input("\nPress ENTER to continue...")

    elif choice == "0":
        break
