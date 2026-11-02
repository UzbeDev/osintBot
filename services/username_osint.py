import asyncio
from services.utils import run_cmd_threaded
from services.ai import query_gemini

async def filter_username_osint_with_ai(username: str, sherlock_raw: str, maigret_raw: str) -> str:
    """Summarizes Sherlock & Maigret output without markdown brackets or headers."""
    prompt = f"""
You are an expert OSINT investigator assistant. Analyze the raw tool results for target username: "{username}".

FORMATTING RULES:
- DO NOT use markdown headers (NO #, ##, ###, ####).
- DO NOT use bracketed markdown links like [Title](url). Write links as plain text: Platform: URL
- Keep the output concise, clean, and direct.

OUTPUT STRUCTURE:
TARGET INTEL:
• Real Name: (detect from bios, metadata, author tags, commits)
• Email / Gmail: (detect any email addresses found)
• Phone Number: (detect any phone numbers found)
• Location / Country: (detect location, e.g. Uzbekistan, CIS, etc.)
• Bios / Persona: (short summary of bios, languages, tech stacks)
• Personal Website: (direct URL if found)

CONFIRMED PROFILES:
(List active confirmed profiles as plain lines, e.g.)
• GitHub: https://github.com/{username}
• Telegram: https://t.me/{username}
• YouTube: URL
(omit generic homepages or false positives like generic discord.com)

RAW SHERLOCK OUTPUT:
{sherlock_raw[:3500]}

RAW MAIGRET OUTPUT:
{maigret_raw[:3500]}
"""
    res = await query_gemini(prompt)
    if res:
        return res
    return "⚠️ AI summary temporarily unavailable. Raw tool outputs are attached below."


async def run_username_osint(username: str) -> tuple[str, str, str]:
    """Runs Sherlock and Maigret concurrently on worker threads and synthesizes findings."""
    clean_username = username.strip().lstrip("@")

    # Run Sherlock & Maigret in parallel on thread pool workers
    sherlock_task = run_cmd_threaded(
        ["sherlock", clean_username, "--timeout", "5", "--print-found"],
        timeout=75,
    )
    maigret_task = run_cmd_threaded(
        ["maigret", clean_username, "--timeout", "5", "--top-sites", "150", "--no-color", "--no-progressbar"],
        timeout=75,
    )

    sherlock_out, maigret_out = await asyncio.gather(sherlock_task, maigret_task)
    ai_summary = await filter_username_osint_with_ai(clean_username, sherlock_out, maigret_out)

    return ai_summary, sherlock_out, maigret_out
