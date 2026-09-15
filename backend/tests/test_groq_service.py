from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.agents.schemas import ExtractedFact, IntentClassification
from app.services.ai_errors import AIServiceUnavailableError, AIStructuredOutputError
from app.services.groq_service import GroqService, pydantic_to_groq_schema


def test_groq_schema_is_strict_and_nullable() -> None:
    schema = pydantic_to_groq_schema(ExtractedFact)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"value", "evidence"}
    assert schema["properties"]["value"]["type"] == ["string", "null"]
    assert schema["properties"]["evidence"]["type"] == ["string", "null"]


def test_structured_completion_uses_configured_model_and_strict_schema() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent":"correction"}'))]
    )
    service = GroqService(
        api_key="test-key-should-not-appear-in-request",
        model="openai/gpt-oss-20b",
        strict=True,
        client=mock_client,
    )

    result = service.structured_completion(
        system_prompt="Classify intent.",
        user_prompt="Sorry, the batch is BMX240602.",
        response_model=IntentClassification,
        schema_name="intent_classification",
    )

    assert result.intent == "correction"
    kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-oss-20b"
    response_format = kwargs["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "intent_classification"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["additionalProperties"] is False
    serialized = str(kwargs)
    assert "test-key-should-not-appear-in-request" not in serialized
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1]["role"] == "user"


def test_missing_api_key_raises_unavailable_without_calling_client() -> None:
    service = GroqService(api_key=None, model="openai/gpt-oss-20b")
    with pytest.raises(AIServiceUnavailableError):
        service.structured_completion(
            system_prompt="x",
            user_prompt="y",
            response_model=IntentClassification,
            schema_name="intent_classification",
        )


def test_invalid_structured_output_raises_safe_error() -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"intent":"not-a-valid-intent"}'))]
    )
    service = GroqService(
        api_key="test-key",
        model="openai/gpt-oss-20b",
        client=mock_client,
    )
    with pytest.raises(AIStructuredOutputError):
        service.structured_completion(
            system_prompt="x",
            user_prompt="y",
            response_model=IntentClassification,
            schema_name="intent_classification",
        )
    with pytest.raises(ValidationError):
        IntentClassification.model_validate({"intent": "not-a-valid-intent"})
