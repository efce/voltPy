class VoltPyNotAllowed(Exception):
    """
    Raise when operation is not allowed for current user.
    """
    pass


class VoltPyDoesNotExists(Exception):
    """
    Raise when object in question does not exists.
    """
    pass


class VoltPyFailed(Exception):
    """
    Raise when any operation failed.
    """
    pass
