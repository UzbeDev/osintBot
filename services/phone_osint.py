from typing import Any
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberType

from services.utils import run_cmd_threaded
from services.ai import query_gemini

def analyze_phone_number(raw_phone: str) -> dict[str, Any]:
    """Analyzes a phone number using Google's libphonenumber."""
    phone_clean = raw_phone.strip()
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean

    try:
        parsed = phonenumbers.parse(phone_clean, None)
    except Exception as e:
        return {"error": f"Invalid phone number format ({e}). Ensure you include country code (e.g. +998901234567)."}

    if not phonenumbers.is_possible_number(parsed):
        return {"error": "Number structure is invalid according to international numbering plans."}

    is_valid = phonenumbers.is_valid_number(parsed)
    region = geocoder.description_for_number(parsed, "en") or "Unknown"
    carrier_name = carrier.name_for_number(parsed, "en") or "Unknown / Landline"
    timezones = list(timezone.time_zones_for_number(parsed))

    ntype = phonenumbers.number_type(parsed)
    type_map = {
        PhoneNumberType.MOBILE: "Mobile",
        PhoneNumberType.FIXED_LINE: "Fixed Line (Landline)",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
        PhoneNumberType.TOLL_FREE: "Toll-Free",
        PhoneNumberType.PREMIUM_RATE: "Premium Rate",
        PhoneNumberType.VOIP: "VoIP (Virtual / Burner Number)",
        PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
        PhoneNumberType.PAGER: "Pager",
        PhoneNumberType.UAN: "Universal Access Number (UAN)",
    }
    line_type = type_map.get(ntype, "Standard / Unknown")

    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    nat = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    digits_only = e164.lstrip("+")
    country_code_str = f"+{parsed.country_code}"
    national_number_str = str(parsed.national_number)

    return {
        "valid": is_valid,
        "e164": e164,
        "international": intl,
        "national": nat,
        "region": region,
        "carrier": carrier_name,
        "line_type": line_type,
        "timezones": timezones,
        "country_code": parsed.country_code,
        "country_code_str": country_code_str,
        "national_number_str": national_number_str,
        "whatsapp_url": f"https://wa.me/{digits_only}",
        "telegram_url": f"https://t.me/+{digits_only}",
        "google_dork": f"https://www.google.com/search?q=%22{e164}%22",
    }


async def filter_phone_osint_with_ai(phone_info: dict[str, Any], ignorant_results: list[str]) -> str:
    """Enriches parsed phone number data with Ignorant registered platforms and OSINT context."""
    registered_platforms = ", ".join(ignorant_results) if ignorant_results else "None detected by scan"

    prompt = f"""
You are an expert OSINT investigator. Analyze the phone number data and registered platforms below:

Phone Data:
- Number (E.164): {phone_info['e164']}
- International: {phone_info['international']}
- Country / Region: {phone_info['region']} (Code: +{phone_info['country_code']})
- Carrier / Operator: {phone_info['carrier']}
- Line Type: {phone_info['line_type']}
- Timezone: {', '.join(phone_info['timezones'])}
- Ignorant Registered Platforms: {registered_platforms}

FORMATTING RULES:
- DO NOT use markdown headers (NO #, ##, ###).
- DO NOT use bracketed links. Use plain URLs.
- Keep it concise (under 1500 chars).

OUTPUT STRUCTURE:
PHONE TELECOM INTEL:
• Standard Number: {phone_info['e164']}
• Country & Region: {phone_info['region']}
• Network Carrier: {phone_info['carrier']}
• Line Classification: {phone_info['line_type']} (Note if VoIP/Burner vs physical SIM)
• Timezone: {', '.join(phone_info['timezones'])}

REGISTERED SERVICES (IGNORANT):
(List detected registered services or state 'None detected')
• ServiceName

DIRECT OSINT LOOKUP LINKS:
• WhatsApp: {phone_info['whatsapp_url']}
• Telegram: {phone_info['telegram_url']}
• Google Search Dork: {phone_info['google_dork']}

INVESTIGATION NOTES:
(2-3 brief tips for reverse-searching this operator/country, e.g. Truecaller, Getcontact, or regional telecom registries)
"""
    res = await query_gemini(prompt)
    if res:
        return res
    return "⚠️ AI insights unavailable."


async def run_phone_osint(raw_phone: str) -> tuple[dict[str, Any], str]:
    """Validates phone number, runs Ignorant in worker thread, and synthesizes report."""
    phone_data = analyze_phone_number(raw_phone)
    if "error" in phone_data:
        return phone_data, ""

    raw_ignorant = await run_cmd_threaded([
        "ignorant",
        phone_data["country_code_str"],
        phone_data["national_number_str"],
        "--only-used",
        "--no-color",
        "--no-clear",
        "-T", "8",
    ], timeout=30)

    ignorant_results = [
        line.replace("[+]", "").strip()
        for line in raw_ignorant.splitlines()
        if "[+]" in line and "Phone number used" not in line
    ]

    ai_summary = await filter_phone_osint_with_ai(phone_data, ignorant_results)
    return phone_data, ai_summary
