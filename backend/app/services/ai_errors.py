"""Internal AI-service errors. Never include prompts, keys, or provider payloads."""


class AIServiceError(Exception):
    """Base class for safe AI processing failures."""


class AIServiceUnavailableError(AIServiceError):
    """Provider missing, unreachable, rate-limited, or otherwise unavailable."""


class AIStructuredOutputError(AIServiceError):
    """Structured model output could not be parsed or validated."""
