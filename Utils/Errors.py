class APIError(Exception):
    def __init__(self, source: str, details=None) -> None:
        print(self)
        self.source = source
        self.details = details

class FailedException(APIError):
    pass


class UnauthorizedException(APIError):
    pass


class NoReplyException(APIError):
    pass


class BadRequestException(APIError):
    def __init__(self, source, errors) -> None:
        self.source = source
        self.errors = errors