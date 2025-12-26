"""
Errors used in Workbench.
"""
class WorkbenchError(Exception):
    """Base class for all Workbench errors."""
    pass

class SerialConnectionError(WorkbenchError):
    """Raised when there is an error with the serial connection."""
    pass
