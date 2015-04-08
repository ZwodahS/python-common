#           DO WHAT THE F*** YOU WANT TO PUBLIC LICENSE
#                   Version 2, December 2004
#
# Copyright (C) 2015- ZwodahS(github.com/ZwodahS)
# zwodahs.github.io
#
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
#           DO WHAT THE F*** YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE F*** YOU WANT TO.
#
# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.
import re
import datetime
import logging

"""
Note:

    1.  Most of the code treat missing key and None value as the same thing.
        For example : is_required field.
"""
#################################### Exceptions ####################################
class DictFieldError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class DictValueError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


#################################### Fields ####################################
class Field(object):

    ERROR_IS_REQUIRED = "required"
    ERROR_TYPE = "type"
    ERROR_VALUE = "value"

    """The parent class of all fields
    It allow for any value to be stored.

    Basic fields values

    is_required                 if true, None value or missing key is not allowed.
    choices                     defines the valid fields for this field.
                                if choices is a dict, a reversed_choices is will also be created.
    default                     default value for this field, either a callable or a value.
                                for callable, a single parameter containing the instance of the field will be provided.
    """

    def __init__(self, is_required=False, choices=None, default=None, **kwargs):
        self.is_required = is_required
        self.choices = choices
        self.default = default

        if isinstance(choices, dict):
            self.reversed_choices = { v : k for k, v in choices.items() }

        for k, v in kwargs.items():
            setattr(self, k, v)

    def errors(self, value, with_key=None):
        if value is None:
            if self.is_required:
                if with_key is not None:
                    yield (with_key, Field.ERROR_IS_REQUIRED)
                else:
                    yield Field.ERROR_IS_REQUIRED
        else:
            if self.choices is not None and value not in self.choices:
                if with_key is not None:
                    yield (with_key, Field.ERROR_VALUE, value)
                else:
                    yield Field.ERROR_VALUE

    def get_errors(self, value):
        return list(self.errors(value))

    def is_valid_value(self, value):
        try:
            next(self.errors(value))
            return False
        except StopIteration:
            return True

    def make_default(self):
        if self.default is None:
            return None
        if callable(self.default):
            return self.default(self)
        else:
            return self.default

    def clean(self, document, key, set_default=True, **kwargs):
        if key not in document:
            if set_default:
                document[key] = self.make_default()

    def update(self, document, key, value):
        document[key] = value


class TypedField(Field):

    def __init__(self, allowed_type, **kwargs):
        super().__init__(**kwargs)
        if allowed_type is None:
            raise DictFieldError(message="Invalid valid for allowed_type : None")
        self.allowed_type = allowed_type

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if value is not None and not isinstance(value, self.allowed_type):
            if with_key is not None:
                yield (with_key, Field.ERROR_TYPE, value)
            else:
                yield Field.ERROR_TYPE


class StringField(TypedField):
    """Typed Field for str

    Additional functionality for string field

    regex               define a regex for this StringField
    """

    def __init__(self, regex=None, **kwargs):
        super().__init__(allowed_type=(str, ), **kwargs)
        if isinstance(regex, str):
            regex = re.compile(regex)
        self.regex = regex


class NumberField(TypedField):
    """Abstract TypedField for number

    Additional value to number field

    min                 define the min value of this number field (inclusive)
    max                 define the max value of this number field (exclusive)

    if choices is defined, min, max will have no effect
    """

    def __init__(self, allowed_type=None, min=None, max=None, **kwargs):
        super().__init__(allowed_type=allowed_type, **kwargs)
        if self.choices is not None:
            self.min = min
            self.max = max
        else:
            self.min = None
            self.max =None

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if value is not None:
            if (self.min is not None and value < self.min) or (self.max is not None and value >= self.max):
                if with_key:
                    yield (with_key, Field.ERROR_VALUE, value)
                else:
                    yield Field.ERROR_VALUE


class IntField(NumberField):
    """TypedField for int
    """

    def __init__(self, **kwargs):
        super().__init__(allowed_type=(int, ), **kwargs)


class FloatField(NumberField):
    """TypedField for float
    """

    def __init__(self, **kwargs):
        super().__init__(allowed_type=(float, int), **kwargs)

    def update(self, document, key, value):
        if isinstance(value, int):
            value = float(value)
        super().update(document, key, value)


class BoolField(TypedField):
    """TypedField for boolean
    """

    def __init__(self, **kwargs):
        super().__init__(allowed_type=(bool, ), **kwargs)


class ListField(TypedField):
    """TypedField for list
    """

    def __init__(self, inner_type=None, **kwargs):
        super().__init__(allowed_type=(list, ), **kwargs)
        if inner_type is not None and not isinstance(inner_type, Field):
            raise DictFieldError(message="Innertype for ListField needs to be a Field")
        self.inner_type = inner_type

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if self.inner_type is not None and isinstance(value, list):
            if with_key is not None:
                for ind, inner in enumerate(value):
                    yield from self.inner_type.errors(inner, ".".join([with_key, str(ind)]))
            else:
                for inner in value:
                    yield from self.inner_type.errors(inner, None)


class DateTimeField(Field):
    """Field used to store datetime object.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if value is not None and not isinstance(value, (datetime.datetime, )):
            if with_key is not None:
                yield (with_key, Field.ERROR_TYPE, value)
            else:
                yield Field.ERROR_TYPE


class DictField(TypedField):
    """Abstract class for Dict
    """

    def __init__(self, **kwargs):
        if "choices" in kwargs:
            raise DictFieldError(message="choices is not allow for DictField or subclass of DictField")
        super().__init__(allowed_type=(dict, ), **kwargs)


    def update(self, document, key, value):
        if isinstance(value, dict):
            if document.get(key) is None:
                document[key] = value
            elif isinstance(document.get(key), dict):
                document[key].update(value)


class MapField(DictField):

    def __init__(self, inner_type=None, **kwargs):
        super().__init__(**kwargs)
        if inner_type is None or not isinstance(inner_type, Field):
            raise DictFieldError(message="Innertype for MapField needs to be a Field")
        self.inner_type = inner_type

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if isinstance(value, dict):
            if with_key is not None:
                for k, v in value.items():
                    yield from self.inner_type.errors(v, ".".join([with_key, k]))
            else:
                for k, v in value:
                    yield from self.inner_type.errors(v, None)

    def update(self, document, key, value):
        if isinstance(value, dict):
            if document.get(key) is None:
                document[key] = {}
        if isinstance(value, dict):
            if isinstance(self.inner_type, DefinedDictField):
                for k, v in value.items():
                    if document[key].get(k) is None:
                        document[key][k] = v
                    else:
                        self.inner_type.model.update(document[key][k], v)
            else:
                for k, v in value.items():
                    if document[key].get(k) is None:
                        document[key][k] = v
                    else:
                        self.inner_type.update(document[key], k, v)


class DefinedDictField(DictField):

    def __init__(self, model, **kwargs):
        if not issubclass(model, DefinedDict):
            raise DictFieldError(message="Model value for DefinedDictField needs to be a DefinedDict")
        super().__init__(**kwargs)
        self.model = model

    def errors(self, value, with_key=None):
        yield from super().errors(value, with_key)
        if isinstance(value, dict):
            yield from self.model._yield_errors(value, parent=with_key)

    def make_default(self):
        if self.default is None:
            return self.model.make_default()
        else:
            return super().make_default()

    def update(self, document, key, value):
        if isinstance(value, dict):
            if document.get(key) is None:
                document[key] = value
            else:
                self.model.update(document[key], value)


#################################### Mixin ####################################
class Mixin(object):
    """Parent class for mixins

    _apply_mixin will be run for each class created with this mixin and each class that inherits a class with this mixin.
    """

    @classmethod
    def _apply_mixin(cls, new_cls, name, bases, cdict):
        """
        cls             The mixin
        new_cls         The new class that is being created
        name            The name of the class
        bases           The bases of the new class (including this mixin)
        cdict           The attributes of the new classes.

        This method is called after all fields are added to new_cls._fields. See DefinedDictMetaClass

        Note, DO NOT modify _fields and _mixins of the new_cls, as they will produce side effects.
        """
        pass

#################################### Documents ####################################
class DefinedDictMetaClass(type):

    def __init__(cls, name, bases, cdict):
        super().__init__(name, bases, cdict)
        cls._fields = {}
        cls._mixins = []
        # stores all fields in _fields
        for base in bases:
            if hasattr(base, "_fields"):
                cls._fields.update(base._fields)
        cls._fields.update({ k : v for k, v in cdict.items() if isinstance(v, Field) })
        # stores all mixin in _mixins, and also retrieve all mixin from parent.
        for base in bases:
            if issubclass(base, Mixin):
                base._apply_mixin(cls, name, bases, cdict)
                cls._mixins.append(base)
            if hasattr(base, "_mixins"):
                for m in base._mixins:
                    m._apply_mixin(cls, name, bases, cdict)
                    cls._mixins.append(m)


class DefinedDict(object, metaclass=DefinedDictMetaClass):

    def __init__(self, **kwargs):
        self.data = kwargs

    @classmethod
    def _yield_errors(cls, document, parent=None):
        for key, definition in cls._fields.items():
            key_string = key if parent is None else ".".join([parent, key])
            value = document.get(key)
            yield from definition.errors(value, with_key=key_string)

    @classmethod
    def get_document_errors(cls, document):
        return list(cls._yield_errors(document))

    @classmethod
    def is_document_valid(cls, document):
        try:
            next(cls._yield_errors(document))
            return False
        except StopIteration:
            return True

    @classmethod
    def make_default(cls):
        return { key : definition.make_default() for key, definition in cls._fields.items() }

    @classmethod
    def clean_document(cls, document, set_default=True, remove_undefined=True):
        if document is None:
            return
        for key, definition in cls._fields.items():
            definition.clean(document, key, set_default=set_default, remove_undefined=remove_undefined)

        if remove_undefined:
            for key in set(document.keys()) - set(cls._fields.keys()) : # remove all the undefined keys
                document.pop(key)

    @classmethod
    def update(cls, document, new_value):
        """
        Recursively update the dictionary
        """
        for key, value in new_value.items():
            if key in cls._fields:
                definition = cls._fields.get(key)
                definition.update(document, key, value)

