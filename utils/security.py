# utils/security.py
import json
import hmac
import hashlib
import requests
import httpx
from fastapi import Request, HTTPException


async def verify_request_signature(request: Request, secret_key: str):
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    # Use the cached body from the middleware or read the body
    body_content = (
        request.state.body if hasattr(request.state, "body") else await request.body()
    )

    # Compute the signature directly from the raw body
    try:
        computed_signature = hmac.new(
            secret_key.encode(), body_content, hashlib.sha256
        ).hexdigest()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to compute signature: {str(e)}"
        )

    if not hmac.compare_digest(signature, computed_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def send_signed_request(url, data, secret_key):
    body = json.dumps(data, separators=(",", ":")).encode()
    signature = hmac.new(secret_key.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }
    response = requests.post(url, headers=headers, data=body)
    return response


async def send_signed_request_async(url, data, secret_key):
    body = json.dumps(data, separators=(",", ":")).encode()
    signature = hmac.new(secret_key.encode(), body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, content=body)
    return response
