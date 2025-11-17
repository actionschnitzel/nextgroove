from enum import IntEnum, auto

class LoginRequestResult(IntEnum):

    SUCCESS = auto()
    FAILURE_GENERIC = auto()
    FAILURE_SELF_SIGNED_SSL = auto()
    FAILURE_CERTIFICATE = auto()
