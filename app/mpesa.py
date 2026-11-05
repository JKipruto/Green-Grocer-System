import os, base64
from datetime import datetime
import requests

def initiate_stk_push(phone: str, amount: float, account_reference: str, description: str):
    """Initiate a Safaricom Daraja STK Push. Returns provider response JSON."""
    key = os.getenv("MPESA_CONSUMER_KEY", "")
    secret = os.getenv("MPESA_CONSUMER_SECRET", "")
    shortcode = os.getenv("MPESA_SHORTCODE", "")
    passkey = os.getenv("MPESA_PASSKEY", "")
    callback = os.getenv("MPESA_CALLBACK_URL", "")
    env = os.getenv("MPESA_ENV", "sandbox").lower()
    if not all([key, secret, shortcode, passkey, callback]):
        raise RuntimeError("M-Pesa is not configured. Add Daraja credentials and a public callback URL to .env.")
    base = "https://api.safaricom.co.ke" if env == "production" else "https://sandbox.safaricom.co.ke"
    token_res = requests.get(
        f"{base}/oauth/v1/generate?grant_type=client_credentials",
        auth=(key, secret), timeout=20
    )
    token_res.raise_for_status()
    token = token_res.json()["access_token"]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": os.getenv("MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline"),
        "Amount": max(1, int(round(amount))),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }
    response = requests.post(
        f"{base}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=25
    )
    response.raise_for_status()
    return response.json()
