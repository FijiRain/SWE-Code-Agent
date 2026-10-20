class ProviderRequestError(Exception):
    pass


class KeyQuotaError(ProviderRequestError):
    pass


class ServerError(ProviderRequestError):
    pass


class FatalError(ProviderRequestError):
    pass
