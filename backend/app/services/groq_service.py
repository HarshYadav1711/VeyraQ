"""Groq provider boundary. Nodes must not construct Groq clients directly."""

from __future__ import annotations

import copy
import json
import logging
from typing import Any, TypeVar

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    Groq,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.ai_errors import AIServiceUnavailableError, AIStructuredOutputError

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


def pydantic_to_groq_schema(model: type[BaseModel]) -> dict[str, Any]:
    raw = copy.deepcopy(model.model_json_schema())
    defs = raw.pop("$defs", {})
    return _normalize_schema(raw, defs)


def _resolve_ref(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema
    name = ref.rsplit("/", 1)[-1]
    resolved = copy.deepcopy(defs[name])
    extras = {key: value for key, value in schema.items() if key != "$ref"}
    resolved.update(extras)
    return _normalize_schema(resolved, defs)


def _normalize_nullable_anyof(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    options = schema.get("anyOf")
    if not isinstance(options, list):
        return schema
    normalized_options = [_normalize_schema(copy.deepcopy(option), defs) for option in options]
    null_options = [item for item in normalized_options if item.get("type") == "null"]
    non_null = [item for item in normalized_options if item.get("type") != "null"]
    if null_options and len(non_null) == 1:
        converted = non_null[0]
        current_type = converted.get("type")
        if isinstance(current_type, str):
            converted["type"] = [current_type, "null"]
        elif isinstance(current_type, list) and "null" not in current_type:
            converted["type"] = [*current_type, "null"]
        return converted
    schema["anyOf"] = normalized_options
    return schema


def _normalize_schema(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        return _resolve_ref(schema, defs)
    if "anyOf" in schema:
        schema = _normalize_nullable_anyof(schema, defs)
        if "anyOf" not in schema:
            return schema

    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        schema["items"] = _normalize_schema(schema["items"], defs)

    properties = schema.get("properties")
    if isinstance(properties, dict):
        schema["type"] = "object"
        schema["properties"] = {
            key: _normalize_schema(value, defs) for key, value in properties.items()
        }
        schema["additionalProperties"] = False
        schema["required"] = list(properties.keys())
        schema.pop("title", None)

    return schema


class GroqService:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        strict: bool = True,
        client: Groq | None = None,
    ) -> None:
        self.model_id = model
        self._api_key = api_key or ""
        self._strict = strict
        self._client = client

    @classmethod
    def from_settings(cls) -> "GroqService":
        return cls(
            api_key=settings.GROQ_API_KEY or None,
            model=settings.GROQ_MODEL,
            strict=settings.GROQ_STRUCTURED_OUTPUT_STRICT,
        )

    def _client_or_raise(self) -> Groq:
        if not self._api_key and self._client is None:
            raise AIServiceUnavailableError("AI processing is unavailable")
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
        return self._client

    def structured_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[TModel],
        schema_name: str,
    ) -> TModel:
        client = self._client_or_raise()
        schema = pydantic_to_groq_schema(response_model)
        try:
            response = client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "strict": self._strict,
                        "schema": schema,
                    },
                },
            )
        except (AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError) as exc:
            logger.warning(
                "groq.unavailable model=%s error_type=%s",
                self.model_id,
                type(exc).__name__,
            )
            raise AIServiceUnavailableError("AI processing is unavailable") from exc
        except APIStatusError as exc:
            logger.warning(
                "groq.status_error model=%s status=%s error_type=%s",
                self.model_id,
                getattr(exc, "status_code", None),
                type(exc).__name__,
            )
            raise AIServiceUnavailableError("AI processing is unavailable") from exc
        except Exception as exc:  # noqa: BLE001 - map unknown SDK failures safely
            logger.warning(
                "groq.unexpected_error model=%s error_type=%s",
                self.model_id,
                type(exc).__name__,
            )
            raise AIServiceUnavailableError("AI processing is unavailable") from exc

        content = None
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError) as exc:
            raise AIStructuredOutputError("Structured output was empty") from exc

        if not content or not str(content).strip():
            raise AIStructuredOutputError("Structured output was empty")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIStructuredOutputError("Structured output was not valid JSON") from exc

        try:
            return response_model.model_validate(payload)
        except ValidationError as exc:
            raise AIStructuredOutputError("Structured output failed validation") from exc
