"""Targeted recapture for Policy Compiler — runs the compile via API first
to ensure the response state is fully ready, then captures the UI."""
from __future__ import annotations

import os
import secrets
import time
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = os.environ.get("VOXPROOF_URL", "http://92.5.42.26:8765")
OUT = Path(__file__).parent / "screenshots"

EXAMPLE_POLICY = """Refund Policy:
- Refunds under $50 can be processed by support agents automatically
- Refunds $50-$500 require supervisor approval before processing
- Refunds above $500 require manager sign-off and identity re-verification

Identity Verification:
- All callers must verify with account number + last 4 digits of SSN
- Identity cannot be bypassed for any reason, regardless of caller authority
- If verification fails 3 times, transfer to fraud department

Data Access:
- Support agents can view individual customer records
- Bulk data exports require written request + compliance approval
- Customer PII must never be shared verbally over phone

Escalation:
- High-value transactions ($500+) must be escalated to manager
- Any request to bypass security protocols triggers fraud alert
- Calls with suspicious patterns should be flagged for review"""


def main():
    # Step 1: warm up the policy compile via API (3-minute timeout)
    print("warming compile via API…", flush=True)
    r = httpx.post(
        f"{BASE}/api/policy/compile",
        json={"policy_text": EXAMPLE_POLICY},
        timeout=240,
    )
    if r.status_code != 200:
        print(f"API failed: {r.status_code} {r.text[:200]}")
        return
    data = r.json()
    if data.get("error"):
        print(f"API returned error: {data['error']}")
        return
    print(f"  API ok: {data.get('rules_count',0)} rules · "
          f"{len(data.get('scenarios',[]))} scenarios · "
          f"yaml len={len(data.get('lobster_yaml',''))}",
          flush=True)

    # Step 2: capture via Playwright, paste the same input, click compile,
    # and wait — should be much faster now since we know the API responds.
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.set_default_timeout(30_000)

        # Auth via API
        unique = secrets.token_hex(4)
        email = f"demo-{unique}@voxproof.local"
        password = "voxproof2026"
        resp = page.request.post(
            f"{BASE}/api/auth/register",
            data={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
        )
        token = resp.json().get("token")
        page.goto(BASE, wait_until="domcontentloaded")
        page.evaluate(f"""
            localStorage.setItem('voxproof_token', {token!r});
            localStorage.setItem('voxproof_user', {email!r});
        """)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector('header', timeout=10_000)
        page.wait_for_timeout(500)

        print("opening Policy Compiler", flush=True)
        page.locator('header nav button:has-text("Policy Compiler")').first.click()
        page.wait_for_timeout(800)

        # Load example by clicking the button, then submit
        page.locator('button:has-text("Load example")').first.click()
        page.wait_for_timeout(400)
        page.locator('button:has-text("Compile Policy")').first.click()
        print("compile clicked — waiting up to 240s", flush=True)
        try:
            page.wait_for_selector(
                'text=/Compiled —|rules ·|attack vector/i',
                timeout=240_000,
            )
            page.wait_for_timeout(2000)
            print("✓ compile result visible", flush=True)
        except Exception:
            print("compile wait timed out — capturing as-is", flush=True)

        page.screenshot(path=str(OUT / "06_policy_compiler.png"), full_page=False)
        print(f"saved {OUT / '06_policy_compiler.png'}", flush=True)
        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
