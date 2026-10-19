from typing import Optional, Protocol, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LocalLLMProvider(Protocol):
    def generate_structured(
        self, 
        prompt: str, 
        response_schema: Type[T], 
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> T:
        """Executes local LLM inference returning guaranteed validated Pydantic models."""
        ...