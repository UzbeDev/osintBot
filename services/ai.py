import asyncio
import logging
from typing import Optional
from google.genai.errors import APIError, ServerError, ClientError

from config import ai_client

async def query_gemini(prompt: str) -> Optional[str]:
    """Queries Gemini with automated fast fallback, 6s timeout, and error recovery."""
    models_to_try = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]

    for model_name in models_to_try:
        try:
            logging.info(f"Generating content via {model_name}...")
            response = await asyncio.wait_for(
                ai_client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                ),
                timeout=6.0,
            )
            if response and response.text:
                return response.text.strip()
        except asyncio.TimeoutError:
            logging.warning(f"Model {model_name} timed out (>6s). Dropping to fallback model immediately...")
        except (ServerError, APIError) as e:
            logging.warning(f"Model {model_name} error: {e}. Dropping to fallback model immediately...")
        except ClientError as e:
            logging.warning(f"Model {model_name} client error: {e}. Trying fallback model...")
        except Exception as e:
            logging.error(f"Unexpected error with {model_name}: {e}")

    return None
