class ProviderRequestError(Exception):
    """Base exception for provider request failures."""

    pass


class KeyQuotaError(ProviderRequestError):
    """Raised when an API key hits rate limits or quota exhaustion."""

    pass


class RequestTooLargeError(ProviderRequestError):
    """Raised when a single request exceeds the provider tokens limit."""

    pass


class ServerError(ProviderRequestError):
    """Raised when the remote provider server encounters an error."""

    pass


class FatalError(ProviderRequestError):
    """Raised on unrecoverable errors like invalid models or requests."""

    pass
