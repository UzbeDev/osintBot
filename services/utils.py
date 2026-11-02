import sys
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path

from config import thread_pool

def resolve_cmd(tool_name: str) -> str:
    """Finds the tool executable in venv/Scripts or system PATH."""
    scripts_dir = Path(sys.executable).parent
    for candidate in [scripts_dir / f"{tool_name}.exe", scripts_dir / tool_name]:
        if candidate.exists():
            return str(candidate)
    which_path = shutil.which(tool_name)
    if which_path:
        return which_path
    return tool_name


def sync_run_cmd(cmd: list[str], timeout: int = 60) -> str:
    """Synchronously executes CLI tools inside thread pool with hard timeout."""
    resolved_cmd = [resolve_cmd(cmd[0])] + cmd[1:]
    try:
        proc = subprocess.run(
            resolved_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return (proc.stdout or proc.stderr).strip()
    except subprocess.TimeoutExpired:
        logging.warning(f"Command {' '.join(cmd[:2])} timed out after {timeout}s.")
        return ""
    except Exception as e:
        logging.error(f"Error running {' '.join(cmd[:2])}: {e}")
        return ""


async def run_cmd_threaded(cmd: list[str], timeout: int = 60) -> str:
    """Dispatches CLI tool execution to thread pool asynchronously."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(thread_pool, sync_run_cmd, cmd, timeout)
