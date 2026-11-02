import json
import asyncio
import hashlib
from typing import Any
import httpx
import dns.resolver

from config import thread_pool
from services.utils import run_cmd_threaded
from services.ai import query_gemini

def resolve_mx_sync(domain: str) -> list[str]:
    """Resolves MX records synchronously in thread pool."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return [str(r.exchange).rstrip(".") for r in answers]
    except Exception:
        return []


async def inspect_email_advanced(email: str) -> dict[str, Any]:
    """Performs deep email OSINT: Threaded DNS/MX inspection, Gravatar, and Google checks."""
    email_clean = email.strip().lower()
    domain = email_clean.split("@")[-1] if "@" in email_clean else ""
    local_part = email_clean.split("@")[0] if "@" in email_clean else ""

    info: dict[str, Any] = {
        "email": email_clean,
        "domain": domain,
        "local_part": local_part,
        "mx_hosts": [],
        "provider": "Unknown",
        "gravatar": None,
        "google_intel": {},
    }

    # 1. Threaded MX Records lookup
    if domain:
        loop = asyncio.get_running_loop()
        info["mx_hosts"] = await loop.run_in_executor(thread_pool, resolve_mx_sync, domain)

        # Provider detection
        mx_str = " ".join(info["mx_hosts"]).lower()
        if "google" in mx_str or domain == "gmail.com":
            info["provider"] = "Google Workspace / Gmail"
        elif "outlook" in mx_str or "microsoft" in mx_str or domain in ["outlook.com", "hotmail.com"]:
            info["provider"] = "Microsoft 365 / Outlook"
        elif "proton" in mx_str or domain in ["proton.me", "protonmail.com"]:
            info["provider"] = "ProtonMail (Encrypted)"
        elif "icloud" in mx_str or domain == "icloud.com":
            info["provider"] = "Apple iCloud Mail"
        elif info["mx_hosts"]:
            info["provider"] = f"Custom Mail Server ({info['mx_hosts'][0]})"

    # 2. Gravatar Lookup
    md5_hash = hashlib.md5(email_clean.encode("utf-8")).hexdigest()
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            grav_res = await client.get(
                f"https://en.gravatar.com/{md5_hash}.json",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if grav_res.status_code == 200:
                data = grav_res.json()
                entries = data.get("entry", [])
                if entries:
                    entry = entries[0]
                    info["gravatar"] = {
                        "displayName": entry.get("displayName"),
                        "preferredUsername": entry.get("preferredUsername"),
                        "currentLocation": entry.get("currentLocation"),
                        "aboutMe": entry.get("aboutMe"),
                        "profileUrl": entry.get("profileUrl"),
                        "accounts": [a.get("url") for a in entry.get("accounts", []) if a.get("url")],
                    }
        except Exception:
            pass

    # 3. Google-specific links & hints
    if "Google" in info["provider"]:
        info["google_intel"] = {
            "calendar_url": f"https://calendar.google.com/calendar/htmlembed?src={email_clean}",
            "hangouts_avatar_hint": f"https://mail.google.com/mail/gxlu?email={email_clean}",
        }

    return info


async def filter_email_osint_with_ai(email_info: dict[str, Any], holehe_results: list[str]) -> str:
    """Summarizes deep email findings with Gemini AI."""
    prompt = f"""
You are an expert OSINT investigator. Synthesize the email intelligence data below for target email: "{email_info['email']}".

FORMATTING RULES:
- DO NOT use markdown headers (NO #, ##, ###).
- DO NOT use bracketed links like [Title](url). Use plain URLs.
- Keep the response short, clear, and actionable.

DATA TO ANALYZE:
- Target Email: {email_info['email']}
- Local Username: {email_info['local_part']}
- Mail Provider / MX: {email_info['provider']} ({', '.join(email_info['mx_hosts'][:3])})
- Gravatar Info: {json.dumps(email_info.get('gravatar') or {})}
- Registered Platforms Detected (Holehe): {', '.join(holehe_results[:25])}

OUTPUT STRUCTURE:
EMAIL IDENTITY INTEL:
• Discovered Name / Handle: (from Gravatar or email pattern)
• Email Provider: (e.g. Google Workspace, Personal Gmail, etc.)
• Gravatar Status: (profile details or none)
• Pivot Username: {email_info['local_part']} (recommend searching this handle)

REGISTERED SERVICES FOUND:
(List the top services where this email is confirmed registered)
• ServiceName

NEXT INVESTIGATION STEPS:
(1-2 short bullet points on pivot actions)
"""
    res = await query_gemini(prompt)
    if res:
        return res
    return "⚠️ AI summary unavailable. Raw results displayed above."


async def run_email_osint(email: str) -> str:
    """Executes threaded Holehe scan, DNS/MX check, Gravatar lookup, and AI synthesis."""
    clean_email = email.strip()

    # Run Holehe on worker thread and DNS/Gravatar concurrently
    holehe_task = run_cmd_threaded(["holehe", clean_email, "--only-used", "--no-color"], timeout=45)
    adv_task = inspect_email_advanced(clean_email)

    holehe_raw, adv_info = await asyncio.gather(holehe_task, adv_task)
    holehe_results = [
        line.replace("[+]", "").strip()
        for line in holehe_raw.splitlines()
        if "[+]" in line
    ]

    return await filter_email_osint_with_ai(adv_info, holehe_results)
