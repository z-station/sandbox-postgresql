from typing import Optional, Any
from app.service import messages


class ServiceException(Exception):
    default_message = None

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Any] = None
    ):
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class CreationException(ServiceException):
    default_message = messages.MSG_1


class DeletionException(ServiceException):
    default_message = messages.MSG_2


class StatusCheckException(ServiceException):
    default_message = messages.MSG_3


class CommandException(ServiceException):
    default_message = messages.MSG_4


class FileNotFound(ServiceException):
    default_message = messages.MSG_5


class ExcecutionException(ServiceException):
    default_message = messages.MSG_6


class InvalidCheckCommand(ServiceException):
    default_message = messages.MSG_7


class CheckException(ServiceException):
    default_message = messages.MSG_8
