from typing import Any
from funstat_api import AsyncFunstatClient, ResolveError
from funstat_api.exceptions import UserHiddenError

from config import FUNSTAT_API_KEY
from services.ai import query_gemini

async def fetch_funstat_intel(target: str) -> dict[str, Any]:
    """Queries Funstat API for Telegram user profile, name history, and group memberships."""
    if not FUNSTAT_API_KEY:
        return {"error": "FUNSTAT_API_KEY is not configured in .env."}

    clean_target = target.strip().lstrip("@")

    try:
        async with AsyncFunstatClient(FUNSTAT_API_KEY) as fs:
            target_id = None
            resolved_info = None

            if clean_target.isdigit():
                target_id = int(clean_target)
            else:
                try:
                    res = await fs.resolve_username(clean_target)
                    if res.data:
                        resolved_info = res.data[0]
                        target_id = resolved_info.id
                    else:
                        return {"error": f"Username @{clean_target} could not be resolved or is not indexed in Funstat."}
                except ResolveError:
                    return {"error": f"Failed to resolve @{clean_target}."}

            if not target_id:
                return {"error": f"Could not determine Telegram User ID for '{clean_target}'."}

            # Fetch stats
            stats_data = None
            try:
                s_res = await fs.stats(target_id)
                stats_data = s_res.data
            except Exception:
                try:
                    s_min = await fs.stats_min(target_id)
                    stats_data = s_min.data
                except Exception:
                    pass

            # Fetch names history
            names_history = []
            try:
                n_res = await fs.get_names(target_id)
                for item in n_res.data:
                    dt = item.date_time.split("T")[0] if "T" in item.date_time else item.date_time
                    names_history.append({"name": item.name, "date": dt})
            except Exception:
                pass

            # Fetch usernames history
            usernames_history = []
            try:
                u_res = await fs.get_usernames(target_id)
                for item in u_res.data:
                    dt = item.date_time.split("T")[0] if "T" in item.date_time else item.date_time
                    usernames_history.append({"username": item.name, "date": dt})
            except Exception:
                pass

            # Fetch chats / public groups
            chats_list = []
            try:
                c_res = await fs.get_chats(target_id)
                for item in c_res.data:
                    chat_obj = item.chat
                    chats_list.append({
                        "title": chat_obj.title,
                        "username": chat_obj.username,
                        "id": chat_obj.id,
                        "messages_count": item.messages_count,
                    })
            except Exception:
                pass

            return {
                "target": clean_target,
                "id": target_id,
                "resolved": resolved_info,
                "stats": stats_data,
                "names": names_history,
                "usernames": usernames_history,
                "chats": chats_list,
            }
    except UserHiddenError:
        return {"error": "🔒 Target user statistics are hidden by privacy settings on Funstat."}
    except Exception as e:
        return {"error": f"Funstat API error: {str(e)}"}


async def format_funstat_report(funstat_data: dict[str, Any]) -> str:
    """Formats Telegram OSINT findings from Funstat and adds AI community insights."""
    stats = funstat_data.get("stats")
    clean_target = funstat_data.get("target")
    target_id = funstat_data.get("id")

    first_name = getattr(stats, "first_name", "") if stats else ""
    about = getattr(stats, "about", "") if stats else ""
    first_seen = getattr(stats, "first_msg_date", "Unknown") if stats else "Unknown"
    last_seen = getattr(stats, "last_msg_date", "Unknown") if stats else "Unknown"
    total_msgs = getattr(stats, "total_msg_count", 0) if stats else 0
    total_groups = getattr(stats, "total_groups", 0) if stats else len(funstat_data.get("chats", []))

    if "T" in str(first_seen):
        first_seen = str(first_seen).split("T")[0]
    if "T" in str(last_seen):
        last_seen = str(last_seen).split("T")[0]

    lines = [
        "TELEGRAM IDENTITY DOSSIER:",
        f"• Immutable User ID: {target_id}",
        f"• Target Handle: @{clean_target}",
        f"• Display Name: {first_name if first_name else 'None'}",
        f"• Bio / About: {about if about else 'None'}",
        f"• First Active: {first_seen}",
        f"• Last Active: {last_seen}",
        f"• Total Public Messages: {total_msgs} messages across {total_groups} indexed groups",
        f"• Direct Profile: https://t.me/{clean_target}",
    ]

    # Name History
    names = funstat_data.get("names", [])
    lines.append("\nPAST NAMES & HANDLES:")
    if names:
        for n in names[:8]:
            lines.append(f"• Name: {n['name']} ({n['date']})")
    usernames = funstat_data.get("usernames", [])
    if usernames:
        for u in usernames[:8]:
            lines.append(f"• Username: @{u['username']} ({u['date']})")
    if not names and not usernames:
        lines.append("• No previous names or handles recorded")

    # Top Public Chats
    chats = funstat_data.get("chats", [])
    lines.append("\nTOP PUBLIC GROUPS & COMMUNITIES:")
    group_titles = []
    if chats:
        for c in chats[:8]:
            title = c["title"]
            group_titles.append(title)
            count = c["messages_count"]
            if c.get("username"):
                lines.append(f"• {title}: https://t.me/{c['username']} ({count} msgs)")
            else:
                lines.append(f"• {title} ({count} msgs)")
    else:
        lines.append("• No public group memberships indexed")

    # AI Community Insights
    if group_titles:
        ai_prompt = f"""
Analyze these public Telegram community group titles: {group_titles}.
Rules:
- DO NOT use markdown headers (NO #, ##, ###).
- DO NOT use bracketed markdown links.
- Write 2 concise sentences summarizing the primary languages, academic/work background, and technical or community interests indicated by these groups.
"""
        ai_insight = await query_gemini(ai_prompt)
        if ai_insight and not ai_insight.lower().startswith("i cannot"):
            lines.append(f"\nCOMMUNITY & PERSONA INSIGHTS:\n{ai_insight.strip()}")

    return "\n".join(lines)


async def run_funstat_osint(target: str) -> tuple[dict[str, Any], str]:
    """Queries Funstat API and formats findings."""
    data = await fetch_funstat_intel(target)
    if "error" in data:
        return data, ""
    report = await format_funstat_report(data)
    return data, report
