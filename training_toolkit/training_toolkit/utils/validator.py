from abc import ABC, abstractmethod
from typing import Optional, Any
from socket import inet_aton
import os

from training_toolkit.logger.log import run_log


class Validator(ABC):
    """
    Interface for parameter validating
    """

    @abstractmethod
    def set_next(self, validator: 'Validator') -> 'Validator':
        pass

    @abstractmethod
    def validate(self, request: Any) -> Optional[bool]:
        pass


class AbstractValidator(Validator):
    """
    The default chaining behavior can be implemented inside a base validator class
    """
    _next_handler: Validator = None

    def set_next(self, validator: 'Validator') -> 'Validator':
        self._next_handler = validator
        return validator

    @abstractmethod
    def validate(self, request: Any) -> Optional[bool]:
        if self._next_handler:
            return self._next_handler.validate(request)
        return True


class IPValidator(AbstractValidator):
    def validate(self, request: Any) -> Optional[bool]:
        try:
            inet_aton(request)
        except OSError:
            run_log.warning(f"not valid ip address: {request}")
            return False
        return super(IPValidator, self).validate(request)


class IntValidator(AbstractValidator):
    def validate(self, request: Any) -> Optional[bool]:
        try:
            int(request)
        except ValueError:
            run_log.warning(f"not valid int value: {request}")
            return False
        return super(IntValidator, self).validate(request)


class RangeValidator(AbstractValidator):
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def validate(self, request: Any) -> Optional[bool]:
        if not (self.start <= int(request) <= self.end):
            run_log.warning(f"not in valid range ({self.start}-{self.end}): {request}")
            return False
        return super(RangeValidator, self).validate(request)


class MultiplicationValidator(AbstractValidator):
    def __init__(self, times: int):
        self.times = times

    def validate(self, request: Any) -> Optional[bool]:
        num = int(request)
        if num > self.times and num % self.times != 0:
            run_log.warning(f"{request} if not multiple of {self.times}")
            return False
        return super(MultiplicationValidator, self).validate(request)


class DirValidator(AbstractValidator):
    def validate(self, request: Any) -> Optional[bool]:
        if not (request and os.path.exists(request) and os.path.isdir(request)):
            run_log.warning(f"dir: '{request}' is not valid or not exist")
            return False
        return super(DirValidator, self).validate(request)
