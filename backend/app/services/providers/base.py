from abc import ABC, abstractmethod
from typing import AsyncIterator
from app.models.schemas import ChatCompletionRequest, ProviderUsageResult


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> ProviderUsageResult:
        """Send a non-streaming chat completion request and return usage + response."""
        ...

    @abstractmethod
    async def chat_completion_stream(
        self,
        request: ChatCompletionRequest,
        api_key: str,
    ) -> AsyncIterator[tuple[str, ProviderUsageResult | None]]:
        """
        Stream a chat completion request.

        Yields tuples of (sse_chunk_string, usage_or_none).
        The final yield should include the ProviderUsageResult.
        All other yields have None for usage.
        """
        ...

    @abstractmethod
    def model_supported(self, model: str) -> bool:
        """Check if this provider handles the given model name."""
        ...
