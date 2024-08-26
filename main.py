import requests
import os
import json
import time

gift_rec = 'violence69.' # - - Put the username of the player


def get_access_token():
    url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    headers = {
        "Authorization": "basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE=",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    auth_code = input("Enter your authorization code: ")

    data = {
        "grant_type": "authorization_code",
        "code": auth_code
    }

    response = requests.post(url, headers=headers, data=data)
    response_data = response.json()

    if 'access_token' in response_data:
        access_token = response_data['access_token']
        account_id = response_data.get('account_id', None)
        if account_id:
            print("Account ID:", account_id)
        else:
            print("Incorrect authoization code")
        print("Access Token:", access_token)
        return access_token, account_id
    else:
        print("Access Token not found in response")
        return None, None

def get_device_info(access_token, account_id):
    if access_token and account_id:
        device_auth_url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{account_id}/deviceAuth"
        device_auth_headers = {
            "Authorization": f"Bearer {access_token}"
        }

        device_auth_response = requests.post(device_auth_url, headers=device_auth_headers)
        device_auth_response_data = device_auth_response.json()

        if 'deviceId' in device_auth_response_data:
            deviceId = device_auth_response_data['deviceId']
            print("Device ID:", deviceId)
        else:
            print("Device ID not found in deviceAuth response")
        if 'secret' in device_auth_response_data:
            secret = device_auth_response_data['secret']
            print("Secret:", secret)
        else:
            print("Secret not found in deviceAuth response")
        return deviceId, secret
    return None, None

def update_config(accountId, deviceId, secret):
  new_config = {
      "accountId": accountId,
      "deviceId": deviceId,
      "secret": secret
  }
  if os.path.exists('config.json'):
      with open('config.json', 'r') as file:
          existing_config = json.load(file)
      already_exists = False
      for config in existing_config:
          if config['accountId'] == new_config['accountId']:
              already_exists = True
              print("Account already in config")
              break
      if not already_exists:
          existing_config.append(new_config)
          with open('config.json', 'w') as file:
              json.dump(existing_config, file, indent=4)
              print("Added account to config")
  else:
      with open('config.json', 'w') as file:
          json.dump([new_config], file, indent=4)
          print("Added account to config")


def get_access_token_with_device_auth(device_id, account_id, secret):
  url = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
  headers = {
      "Authorization": "basic MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE=",
      "Content-Type": "application/x-www-form-urlencoded"
  }

  data = {
      "grant_type": "device_auth",
      "device_id": device_id,
      "account_id": account_id,
      "secret": secret
  }

  response = requests.post(url, headers=headers, data=data)
  response_data = response.json()

  if 'access_token' in response_data:
      return response_data['access_token']
  else:
      return None


def get_offers():
  url = "https://mewtwos.xyz/offers/shop" # - - Dead Link... Replace with your shop offer api
  response = requests.get(url)
  if response.status_code == 200:
      return response.json()
  else:
      print("Failed to fetch offers")
      return []


def main():
  choice = input("""
  Made & Developed by @.t.wc & mewtwo#0001

  [1] Add account to config

  [2] Gift entire item-shop

  [3] Send friend request
  \n
  Choice: """)
  if choice == '1':
      os.system('cls' if os.name == 'nt' else 'clear')
      access_token, account_id = get_access_token()
      device_id, secret = get_device_info(access_token, account_id)
      if account_id and device_id and secret:
          update_config(account_id, device_id, secret)
  elif choice == '2':
    os.system('cls' if os.name == 'nt' else 'clear')
    if os.path.exists('config.json'):
        with open('config.json', 'r') as file:
            account_data = json.load(file)

        for i, account_info in enumerate(account_data):
            device_id = account_info['deviceId']
            secret = account_info['secret']
            access_token = get_access_token_with_device_auth(device_id, account_info['accountId'], secret)

            if access_token:
                display_name = get_display_name(access_token)
                if display_name:
                    print(f"[{account_info['accountId']}] Gift Receiver : {display_name}")
                    offers = get_offers()
                    for offer in offers:
                        offer_id = offer["offerId"]
                        final_price = offer["price"]
                        id = account_info['accountId']
                        send_gift_request(id, access_token, offer_id, final_price, display_name)
                        time.sleep(1)
                else:
                    print(f"[{account_info['accountId']}] Failed to retrieve gift receiver id")
            else:
                print(f"[{account_info['accountId']}] Failed to obtain access token")

            if i == len(account_data) - 1:
                print("Reached the end of the account list, starting over.")
                i = -1
    else:
          print("No accounts found in config.")
  elif choice == '3':
      os.system('cls' if os.name == 'nt' else 'clear')
      if os.path.exists('config.json'):
          with open('config.json', 'r') as file:
              account_data = json.load(file)
          for account_info in account_data:
              device_id = account_info['deviceId']
              secret = account_info['secret']
              access_token = get_access_token_with_device_auth(device_id, account_info['accountId'], secret)
              if access_token:
                  print(f"[{account_info['accountId']}] Sent friend request to gift receiver")
                  send_friend_request(account_info['accountId'], access_token)
              else:
                  print(f"Failed to obtain access token for {account_info['accountId']}")
  else:
      print("Invalid choice.")


def send_friend_request(account_id, access_token):
  friend_id = get_display_name(access_token)
  url = f"https://friends-public-service-prod.ol.epicgames.com/friends/api/v1/{account_id}/friends/{friend_id}"
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}"
  }

  response = requests.post(url, headers=headers)

def send_gift_request(account_id, access_token, offer_id, final_price, user_id):
  url = f"https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/game/v2/profile/{account_id}/client/GiftCatalogEntry?profileId=common_core"
  payload = {
      "offerId": offer_id,
      "currency": "MtxCurrency",
      "currencySubType": "",
      "expectedTotalPrice": final_price,
      "gameContext": "Frontend.CatabaScreen",
      "receiverAccountIds": [user_id],
      "giftWrapTemplateId": "",
      "personalMessage": ""
  }
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}"
  }

  response = requests.post(url, json=payload, headers=headers)
  with open('config.json', 'r') as file:
    account_data = json.load(file)
  for account_info in account_data:
    device_id = account_info['deviceId']
    secret = account_info['secret']
  if response.status_code == 200:
    print(f"[{account_info['accountId']}] Sent cosmetic gift to {user_id}")


def get_display_name(access_token):
  url = f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/displayName/{gift_rec}"
  headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {access_token}"
  }

  response = requests.get(url, headers=headers)

  if response.status_code == 200:
      response_data = response.json()
      display_name = response_data.get('id', None)
  else:
      print("Failed to retrieve display name.")

  if response.status_code == 200:
      response_data = response.json()
      return response_data.get('id', None)
  else:
      return None

if __name__ == "__main__":
    main()
