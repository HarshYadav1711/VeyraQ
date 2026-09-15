from typing import Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class AIService(Protocol):
    """Provider-agnostic structured completion boundary used by LangGraph nodes."""

    model_id: str

    def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
        schema_name: str,
    ) -> TModel: ...
