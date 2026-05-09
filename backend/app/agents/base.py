import time
import uuid
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db.models import AgentLog


class BaseAgent(ABC):
    def __init__(self, db: AsyncSession, model: Optional[str] = None):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.db = db
        self.model = model or settings.anthropic_model_smart

    @property
    def model_fast(self) -> str:
        return settings.anthropic_model_fast

    @property
    def model_smart(self) -> str:
        return settings.anthropic_model_smart

    @abstractmethod
    async def run(self, input: dict, session_context: dict) -> dict:
        """Takes input + session context, returns structured output."""

    async def _call_llm(
        self,
        messages: List[dict],
        system: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> str:
        start = time.monotonic()
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.anthropic_max_tokens,
                system=system,
                messages=messages,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            text = response.content[0].text
            await self._log(
                model=self.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
                session_id=session_id,
            )
            return text
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log(
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(exc),
                session_id=session_id,
            )
            raise

    async def _call_llm_stream(
        self,
        messages: List[dict],
        system: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> AsyncGenerator[str, None]:
        start = time.monotonic()
        total_input = 0
        total_output = 0
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=settings.anthropic_max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                final = await stream.get_final_message()
                total_input = final.usage.input_tokens
                total_output = final.usage.output_tokens
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log(
                model=self.model,
                input_tokens=total_input,
                output_tokens=total_output,
                latency_ms=latency_ms,
                session_id=session_id,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log(
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(exc),
                session_id=session_id,
            )
            raise

    async def _log(
        self,
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
    ) -> None:
        log = AgentLog(
            session_id=session_id,
            agent_type=type(self).__name__,
            model_used=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.flush()
