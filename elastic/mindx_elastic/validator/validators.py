#!/usr/bin/python3
# -*- coding: utf-8 -*-
#   Copyright (C)  2022. Huawei Technologies Co., Ltd. All rights reserved.
import os
import re
import sys
from typing import Callable, Any
from typing import List, Union, Optional, Tuple


class Validator:
    """
    A validator to check the input parameters
    """

    def __init__(self, value, msg="value is invalid"):
        """
        :param value: the value for validation
        :param msg: default error msg
        """
        self.value = value
        self.msg = msg
        self.checkers = []
        self.is_valid_state = None

    def register_checker(self, checker: Callable[[Any], bool], msg: str = None):
        self.checkers.append((checker, msg if msg else self.msg))

    def check(self):
        if self.is_valid_state is None:
            self.is_valid_state = True
        for ck, msg in self.checkers:
            self.is_valid_state &= ck(self.value)
            if not self.is_valid_state:
                self.msg = msg
                break
        if self.is_valid_state:
            self.msg = None
        return self

    def is_valid(self):
        if self.is_valid_state is None:
            self.check()
        return self.is_valid_state

    def get_value(self, default=None):
        return self.value if self.is_valid() else default


class StringValidator(Validator):
    """
    String type validator.
    """

    def __init__(self, value, max_len=None, min_len=0):
        super().__init__(value)
        self.register_checker(lambda x: isinstance(x, str), "type is not str")
        if min_len is not None:
            self.register_checker(lambda x: len(x) >= min_len, f"length is less than {min_len}")
        if max_len is not None:
            self.register_checker(lambda x: len(x) <= max_len, f"length is bigger than {max_len}")

    def should_match_regexes(self, regexes: str, msg=None):
        if isinstance(regexes, str):
            all_regexes = [regexes]
        elif isinstance(regexes, list):
            all_regexes = regexes
        else:
            raise ValueError("regexes are not str or list")

        for pattern in all_regexes:
            self.register_checker(lambda x: True if re.match(pattern, x) else False, msg)
        return self

    def exclusive_chars(self, chars: Union[List[str], str], msg=None):
        if isinstance(chars, str):
            all_chars = [chars]
        elif isinstance(chars, list):
            all_chars = chars
        else:
            raise ValueError("exclusive chars are not str or list")

        for char in all_chars:
            self.register_checker(lambda x: char not in x, msg)

    def can_be_transformed2int(self, min_value: int = None, max_value: int = None):
        self.register_checker(lambda x: x is not None and x.isdigit())
        if min_value is None:
            min_value = -sys.maxsize - 1
        if max_value is None:
            max_value = sys.maxsize

        can_transformed = self.value.isdigit()
        try:
            if can_transformed and (min_value > int(self.value) or max_value < int(self.value)):
                can_transformed = False
        except ValueError:
            can_transformed = False
        finally:
            if self.is_valid_state is not None:
                self.is_valid_state &= can_transformed
            else:
                self.is_valid_state = can_transformed
        return self


class MapValidator(Validator):
    """
    Map type validator.
    """

    def __init__(self, value: dict, inclusive_keys: list = None):
        super().__init__(value)
        self.register_checker(lambda x: isinstance(x, dict), "type is not dict")
        if inclusive_keys is None:
            inclusive_keys = []
        for key in inclusive_keys:
            self.register_checker(lambda x: key in self.value, "Key error for the value of dict type")


class DirectoryValidator(StringValidator):
    def __init__(self, value, max_len=None, min_len=1, should_not_be_a_soft_link=False):
        """
        @param value: the path, should not be emtpy string, should not contain double dot(../)
        @param should_not_be_a_soft_link: require path is an absolute path and should not contain soft link
        """
        path = value
        can_be_a_real_path = True
        msg = ""

        try:
            path = os.path.realpath(value)
            if value is None or '..' in value or len(value) < min_len or \
                    (len(value) > max_len if max_len is not None else False):
                can_be_a_real_path = False
                msg = "the path parameter is valid"
            elif should_not_be_a_soft_link and path != os.path.normpath(value):
                msg = "soft link or relative path should not be in the path parameter"
                can_be_a_real_path = False
        except (ValueError, TypeError):
            can_be_a_real_path = False
            msg = "path parameter cannot be transformed to a valid path"
        finally:
            super().__init__(path, max_len, min_len)
            self.check()
            if self.is_valid_state:
                self.is_valid_state = can_be_a_real_path
                self.msg = msg

    def path_should_exist(self, is_file=True, msg=None):
        self.register_checker(lambda path: os.path.exists(self.value),
                              msg if msg else "path parameter does not exist")
        if is_file:
            self.register_checker(lambda path: os.path.isfile(self.value),
                                  msg if msg else "path parameter is not a file")
        return self

    def path_should_not_exist(self):
        self.register_checker(lambda path: not os.path.exists(self.value), "path parameter does not exist")
        return self

    def with_blacklist(self, lst: List = None, exact_compare: bool = True, msg: str = None):
        if lst is None:
            lst = ["/usr/bin", "/usr/sbin", "/etc", "/usr/lib", "/usr/lib64"]
        if len(lst) == 0:
            return self
        if msg is None:
            msg = "path should is in blacklist"
        if exact_compare:
            self.register_checker(lambda path: path not in [os.path.realpath(each) for each in lst], msg)
        else:
            self.register_checker(
                lambda path: not any([DirectoryValidator._check_is_children_path(each, path) for each in lst]), msg
            )
        return self

    @staticmethod
    def _remove_prefix(string: Optional[str], prefix: Optional[str]) -> Tuple[bool, Optional[str]]:
        if string is None or prefix is None or len(string) < len(prefix):
            return False, string
        if string.startswith(prefix):
            return True, string[len(prefix):]
        else:
            return False, string

    @staticmethod
    def _check_is_children_path(path_: str, target_: str):
        if not target_:
            return False
        try:
            realpath_ = os.path.realpath(path_)
            realpath_target = os.path.realpath(target_)
            is_prefix, rest_part = DirectoryValidator._remove_prefix(realpath_target, realpath_)
            if rest_part.startswith(os.path.sep):
                rest_part = rest_part.lstrip(os.path.sep)
            if is_prefix:
                joint_path = os.path.join(realpath_, rest_part)
                return os.path.realpath(joint_path) == realpath_target
            else:
                return False
        except Exception as _:
            return False
        finally:
            pass

    def should_not_contains_sensitive_words(self, words: List = None, msg=None):
        if words is None:
            words = ["Key", "password", "privatekey"]
        self.register_checker(lambda path: DirectoryValidator.__check_with_sensitive_words(path, words), msg)
        return self

    @staticmethod
    def __check_with_sensitive_words(path: str, words: List):
        _, name = os.path.split(path)
        if name:
            return not any(map(lambda x: x in path, words))
        else:
            return False
