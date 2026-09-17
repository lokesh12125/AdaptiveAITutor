"""Optional OpenAI enrichment with strict timeout and deterministic fallbacks."""
import logging
from openai import OpenAI
from typing import Optional
from ..config import OPENAI_API_KEY, OPENAI_MODEL, api_key_configured

logger = logging.getLogger("tutor.llm")


class TutorLLM:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=OPENAI_API_KEY, timeout=8.0) if api_key_configured() else None
        self.mode = "live" if self._client else "demo"
        self.last_was_fallback = not bool(self._client)

    def tutor_reply(self, prompt: str, fallback: str, system_prompt: Optional[str] = None) -> str:
        if not self._client or self.mode == "demo":
            self.last_was_fallback = True
            return fallback
        sys_msg = system_prompt or "You are a concise Python tutor. Give a Socratic hint; never provide a complete solution."
        try:
            response = self._client.responses.create(
                model=OPENAI_MODEL,
                input=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}
                ],
                max_output_tokens=300,
                timeout=8.0,
            )
            text = response.output_text.strip()
            if text:
                self.last_was_fallback = False
                return text
        except Exception as err:
            logger.warning("LLM request failed or timed out: %s. Degrading to demo mode.", type(err).__name__)
            self.mode = "demo"
            self._client = None
            self.last_was_fallback = True
        return fallback


llm = TutorLLM()
