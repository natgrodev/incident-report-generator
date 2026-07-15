"""
Core logic: talk to the model, get a report and a gap analysis.

Kept separate from the UI so it can be used from a script, a web app, or
eventually an API without rewriting anything.
"""

import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import REPORT_PROMPT, GAPS_PROMPT

MODEL = "gemini-flash-latest"

# Failures worth retrying rather than surfacing to the user:
#   503 / UNAVAILABLE       - the model is overloaded
#   429 / RESOURCE_EXHAUSTED - rate limited
#   500 / INTERNAL          - a server-side blip
RETRYABLE = ("503", "429", "500", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "INTERNAL")
MAX_ATTEMPTS = 4


def get_client():
    """Return a configured client, or raise with a useful message."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY not found. Create a .env file containing:\n"
            "    GOOGLE_API_KEY=your_key_here"
        )

    return genai.Client(api_key=api_key)


def _is_retryable(error):
    """Might this error succeed if we simply wait and try again?"""
    text = str(error)
    return any(code in text for code in RETRYABLE)


def _call(client, system_prompt, source_text, source_type, temperature):
    """
    One call to the model, with retries.

    Someone else's server will be overloaded at some point. A tool used at 3am
    after a P1 should absorb that, not hand the user a stack trace.
    """
    label = "call transcript" if source_type == "transcript" else "incident notes"

    user_message = (
        f"The source below is a {label} from an IT incident.\n\n"
        f"---\n{source_text}\n---"
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
    )

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_message,
                config=config,
            )
            return response.text

        except Exception as e:
            # Not something waiting will fix, or we're out of attempts: give up.
            if not _is_retryable(e) or attempt == MAX_ATTEMPTS - 1:
                raise

            # Back off: 2s, 4s, 8s — give the overloaded model time to recover.
            time.sleep(2 ** (attempt + 1))


def generate_report(client, source_text, source_type="notes"):
    """Generate the post-incident report itself."""
    # Low temperature: this is a structuring task. Creativity here is a bug.
    return _call(client, REPORT_PROMPT, source_text, source_type, temperature=0.2)


def find_gaps(client, source_text, source_type="notes"):
    """Identify what's missing from the source, for the author's eyes only."""
    return _call(client, GAPS_PROMPT, source_text, source_type, temperature=0.1)
