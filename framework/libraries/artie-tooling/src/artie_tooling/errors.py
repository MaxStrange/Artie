"""
Module for common errors used in Artie Tooling.
"""
class ArtieToolingError(Exception):
    """
    Base class for all Artie Tooling errors.
    """
    pass

class HTTPError(ArtieToolingError):
    """
    Raised when an HTTP error occurs.
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {status_code}: {message}")
