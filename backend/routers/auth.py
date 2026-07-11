import logging
import os
import jwt
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
from wikibaseintegrator.wbi_login import OAuth1

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_OAUTH_URL = "https://www.wikidata.org/w/index.php?title=Special:OAuth"
USER_AGENT = "osm-wikidata-matcher-neo 1.0 (https://github.com/anomalyco/opencode)"

TOKENS_FILE = Path(__file__).parent.parent.parent / ".tokens"


def load_tokens() -> dict:
    """Load tokens from .tokens file"""
    if not TOKENS_FILE.exists():
        return {}
    tokens = {}
    content = TOKENS_FILE.read_text()
    for line in content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_')
            if value.strip():
                tokens[key] = value.strip()
    return tokens


def save_tokens(tokens: dict):
    """Save tokens to .tokens file"""
    lines = [
        "",
        "",
        "Client application key",
        f"    {tokens.get('client_application_key', '')}",
        "Client application secret",
        f"    {tokens.get('client_application_secret', '')}",
        "Access token",
        f"    {tokens.get('access_token', '')}",
    ]
    TOKENS_FILE.write_text('\n'.join(lines))


tokens = load_tokens()
ACCESS_TOKEN = tokens.get('access_token', os.getenv("WIKIMEDIA_ACCESS_TOKEN", ""))
CONSUMER_KEY = tokens.get('client_application_key', os.getenv("WIKIMEDIA_CLIENT_KEY", ""))
CONSUMER_SECRET = tokens.get('client_application_secret', os.getenv("WIKIMEDIA_CLIENT_SECRET", ""))


class AuthStatus(BaseModel):
    logged_in: bool
    username: str | None = None


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None


async def verify_token(access_token: str) -> tuple[bool, str | None]:
    """Verify token and return (is_valid, username)"""
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {access_token}"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                WIKIDATA_API_URL,
                params={"action": "query", "meta": "userinfo", "format": "json"},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                username = data.get("query", {}).get("userinfo", {}).get("name")
                return True, username
    except Exception as e:
        log.warning(f"Token verification failed: {e}")
    return False, None


@router.get("/status", response_model=AuthStatus)
async def auth_status():
    if not ACCESS_TOKEN:
        return AuthStatus(logged_in=False)

    token_data = decode_token(ACCESS_TOKEN)
    if not token_data:
        return AuthStatus(logged_in=False)

    is_valid, username = await verify_token(ACCESS_TOKEN)
    if is_valid and username:
        return AuthStatus(logged_in=True, username=username)

    if not username and token_data.get("sub"):
        username = f"User:{token_data['sub']}"

    if username:
        return AuthStatus(logged_in=True, username=username)

    return AuthStatus(logged_in=False)


@router.get("/login")
async def login():
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise HTTPException(status_code=503, detail="OAuth not configured - set credentials in .tokens file")

    oauth = OAuth1(
        consumer_token=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
    )

    try:
        redirect_url, request_token = oauth.initiate()
        log.info(f"OAuth initiation successful, redirect to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        log.error(f"OAuth initiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth initiation failed: {str(e)}")


@router.get("/callback")
async def callback(request: Request, oauth_verifier: str = None, oauth_token: str = None):
    if not oauth_verifier or not oauth_token:
        raise HTTPException(status_code=400, detail="Missing OAuth verifier or token")

    oauth = OAuth1(
        consumer_token=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
    )

    try:
        oauth.continue_oauth(oauth_token, oauth_verifier)
        access_token = oauth.access_token
        access_secret = oauth.access_secret

        log.info("OAuth callback successful, got access token")

        global ACCESS_TOKEN
        ACCESS_TOKEN = access_token
        tokens['access_token'] = access_token
        save_tokens(tokens)

        return {"status": "ok", "username": "Authenticated"}
    except Exception as e:
        log.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.post("/logout")
async def logout():
    global ACCESS_TOKEN
    ACCESS_TOKEN = ""
    tokens['access_token'] = ""
    save_tokens(tokens)
    return {"status": "ok"}
