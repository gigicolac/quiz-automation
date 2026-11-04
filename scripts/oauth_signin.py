#!/usr/bin/env python3
"""One-time sign-in that connects GitHub to Canva or YouTube.

Run twice from the "Sign in" workflow:
  1. with no redirect URL: prints a sign-in link (written to the job summary)
  2. with the address the browser landed on after approving (http://127.0.0.1:3001/oauth/redirect?code=...):
     swaps the code for a long-lived refresh token and saves it as a repository secret.

The browser page at 127.0.0.1 will not load. That is expected; only its address is needed.

Env: SERVICE (canva|youtube), REDIRECT_URL (optional), <SERVICE>_CLIENT_ID / _CLIENT_SECRET,
GH_SECRETS_TOKEN (to save the refresh token), GITHUB_REPOSITORY, GITHUB_STEP_SUMMARY.
"""
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

REDIRECT = "http://127.0.0.1:3001/oauth/redirect"

SERVICES = {
    "canva": {
        "id_env": "CANVA_CLIENT_ID", "secret_env": "CANVA_CLIENT_SECRET", "save_as": "CANVA_REFRESH_TOKEN",
        "authorize": "https://www.canva.com/api/oauth/authorize",
        "token": "https://api.canva.com/rest/v1/oauth/token",
        "scope": "asset:read asset:write brandtemplate:content:read brandtemplate:meta:read "
                 "design:content:read design:content:write design:meta:read",
        "extra": {"code_challenge_method": "s256"},
        "basic_auth": True,
    },
    "youtube": {
        "id_env": "YT_CLIENT_ID", "secret_env": "YT_CLIENT_SECRET", "save_as": "YT_REFRESH_TOKEN",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/youtube.force-ssl",
        "extra": {"code_challenge_method": "S256", "access_type": "offline", "prompt": "consent"},
        "basic_auth": False,
    },
}


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def verifier(secret, service):
    # Derived from the client secret so both runs agree without storing anything.
    return b64url(hashlib.sha256(f"quiz-automation:{service}:{secret}".encode()).digest() * 2)[:64]


def summary(text):
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(text + "\n")


def main():
    service = os.environ["SERVICE"]
    cfg = SERVICES[service]
    # secrets pasted with a stray space or line break make the provider reject the client ID
    cid = (os.environ.get(cfg["id_env"]) or "").strip()
    secret = (os.environ.get(cfg["secret_env"]) or "").strip()
    if not cid or not secret:
        sys.exit(f"Missing repository secrets {cfg['id_env']} / {cfg['secret_env']}.")
    ver = verifier(secret, service)
    challenge = b64url(hashlib.sha256(ver.encode()).digest())
    landed = os.environ.get("REDIRECT_URL", "").strip()

    if not landed:
        params = {"client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
                  "scope": cfg["scope"], "code_challenge": challenge, "state": service, **cfg["extra"]}
        link = cfg["authorize"] + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        summary(f"## {service.title()} sign-in, step 1\n\nClient ID in use: `{cid[:6]}…{cid[-4:]}` "
                f"({len(cid)} characters). Check it matches the developer portal.\n\n1. Open this link and approve: [Sign in to {service.title()}]({link})\n"
                "2. The browser ends on a page that won't load (127.0.0.1). That's expected.\n"
                "3. Copy the full address from the address bar and run this workflow again with it pasted "
                "into **Redirect URL**, within a few minutes.")
        return

    query = urllib.parse.parse_qs(urllib.parse.urlparse(landed).query)
    if "error" in query:
        sys.exit(f"Sign-in was not approved: {query['error'][0]}")
    code = query.get("code", [None])[0]
    if not code:
        sys.exit("No code found in the redirect URL. Paste the whole address from the browser.")
    print(f"::add-mask::{code}")

    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "code_verifier": ver}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if cfg["basic_auth"]:
        headers["Authorization"] = "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()
    else:
        form.update(client_id=cid, client_secret=secret)
    req = urllib.request.Request(cfg["token"], data=urllib.parse.urlencode(form).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed ({e.code}): {e.read().decode()[:300]}. "
                 "Codes expire after a few minutes: run step 1 again for a fresh link.")
    refresh = tok.get("refresh_token")
    if not refresh:
        sys.exit("No refresh token returned. For YouTube, remove the app's access at "
                 "myaccount.google.com/permissions and sign in again.")
    print(f"::add-mask::{refresh}")

    gh_token = (os.environ.get("GH_SECRETS_TOKEN") or "").strip()
    if not gh_token:
        sys.exit("Missing repository secret GH_SECRETS_TOKEN, needed to save the refresh token.")
    env = {**os.environ, "GH_TOKEN": gh_token}
    subprocess.run(["gh", "secret", "set", cfg["save_as"], "-R", os.environ["GITHUB_REPOSITORY"]],
                   input=refresh.encode(), env=env, check=True)
    summary(f"## {service.title()} sign-in complete\n\nSaved repository secret `{cfg['save_as']}`. "
            "Nothing else to do.")


if __name__ == "__main__":
    main()
