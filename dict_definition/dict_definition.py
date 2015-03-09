
import datetime
import logging
import re

class FieldError(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

#################################### Field Definitions ####################################
class Field(object):
    """The parent class of all fields.

    It allow for any type keyword to be stored, which allow for additional mixin without modifying the main dict_definition.

    Basic field values are

    is_required             defines if this field is required
    choices                 defines what is the possible of this field is, allow for either list or dict.
                            if choices is a dict, a reversed_choices dictionary will also be stored.
    default                 default value for this field, either a callable or a value.
                            if a callable is used, a single value containing the instance of the field will be pass to it
    """

    def __init__(self, is_required=False, choices=None, default=None, **kwargs):

        self.is_required = is_required
        self.choices = choices
        self.default = default

        if isinstance(choices, dict):
            self.reversed_choices = { v : k for k, v in choices.items() }

        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_error(self, value):
        if not self.is_valid_type(value):
            return ("type", value)
        if self.choices is not None and value not in self.choices:
            return ("value", value)
        return None

    def get_default_value(self):
        if self.default is None:
            return None
        if callable(self.default):
            return self.default(self)
        else:
            return self.default

    def is_valid_type(self, value):
        if not hasattr(self, "type"):
            return True
        if value is None:
            return True
        return isinstance(value, self.type)

class StringField(Field):
    """The String field subclass of field

    Additional value to string field

    regex               define a regex for this stringfield
    """

    def __init__(self, regex=None, **kwargs):
        super().__init__(**kwargs)
        if isinstance(regex, str):
            regex = re.compile(regex)
        self.regex = regex
        self.type = str

    def get_error(self, value):
        parent_error = super().get_error(value)
        if parent_error is not None:
            return parent_error
        if self.regex is not None and not self.regex.match(value):
            return ("value", value)
        return None


class NumberField(Field):
    """The Number Field subclass of field

    Additional value to number field

    min                 define the min value of this number field
    max                 define the max value of this number field

    if choices is defined, min, max will have no effect
    """

    def __init__(self, min=None, max=None, **kwargs):
        super().__init__(**kwargs)
        if self.choices is None:
            self.min = min
            self.max = max
        else:
            self.min = None
            self.max = None

    def get_error(self, value):
        parent_error = super().get_error(value)
        if parent_error is not None:
            return parent_error

        if value is None:
            return None

        if (self.min is not None and value < self.min) or (self.max is not None and value >= self.max):
            return ("value (out of range)", value)

        return None


class IntField(NumberField):
    """Define int field
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = int


class FloatField(NumberField):
    """Define float Field
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = (float, int)


class BoolField(Field):
    """Define Bool Field
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = bool


class ListField(Field):
    """Define a list

    Addtiional value to list field

    inner_type              define the inner type of the list field. Must be a instance of Field
    """

    def __init__(self, inner_type=None, **kwargs):
        super().__init__(**kwargs)
        self.type = list
        if inner_type is not None and not isinstance(inner_type, Field):
            raise FieldError(message="Invalid type for inner_type {0} for ListField".format(type(inner_type)))
        self.inner_type = inner_type

    def get_error(self, value):
        paraent_error = super().get_error(value)
        if parent_error is not None:
            return parent_error

        if value is None:
            return None

        if self.inner_type is not None:
            for inner in value:
                error = self.inner_type.get_error(inner)
                if error is not None:
                    return error

        return None


class DictField(Field):
    """Define a dict
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = dict


class DefinedDictField(DictField):
    """Define a defineddict
    """

    def __init__(self, model, **kwargs):
        if not issubclass(model, DefinedDict):
            raise FieldError(message="Invalid model class for model field {0}".format(type(model)))

        super().__init__(**kwargs)
        self.model = model

    def get_default_value(self):
        return self.model.make_default()


class DateTimeField(Field):
    """Define a datetime field
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.type = datetime.datetime


#################################### End of Fields ####################################

#################################### Mixin parent ####################################
class Mixin(object):
    """
    A parent class for mixin.

    _apply_mixin will be run for each class created with this mixin
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
        """
        pass
#################################### End of mixin ####################################

#################################### Defined Dict ####################################
class DefinedDictMetaClass(type):

    def __init__(cls, name, bases, cdict):
        super().__init__(name, bases, cdict)
        cls._fields = {}
        cls._mixins = []
        new_fields = { k : v for k, v in cdict.items() if isinstance(v, Field) }
        # retrieve what is previously defined.
        for base in bases:
            if hasattr(base, "_fields"):
                cls._fields.update(base._fields)
        cls._fields.update(new_fields) # override _fields with the new one defined
        for base in bases:
            if issubclass(base, Mixin):
                base._apply_mixin(cls, name, bases, cdict)
                cls._mixins.append(base)


class DefinedDict(object, metaclass=DefinedDictMetaClass):

    @classmethod
    def _get_document_errors(cls, document, parent=None):
        for key, definition in cls._fields.items():
            key_string = key if not parent else ".".join([parent, key])
            if key in document:
                value = document.get(key)
                error = definition.get_error(value)
                if error is not None:
                    yield (key_string, ) + error # combine the tuples
                if isinstance(definition, DefinedDictField):
                    yield from definition.model._get_document_errors(document.get(key), parent=key_string)
            elif definition.is_required:
                yield (key_string, "required")

    @classmethod
    def get_document_errors(cls, document):
        return list(cls._get_document_errors(document))

    @classmethod
    def is_valid(cls, document):
        try:
            next(cls._get_document_errors(document))
            return False
        except StopIteration:
            return True

    @classmethod
    def make_default(cls):
        default = {}
        for key, definition in cls._fields.items():
            if definition.default is not None:
                default[key] = definition.get_default_value()
        return default

    @classmethod
    def clean(cls, document, set_default=True, remove_undefined=True, allow_none=False, populate_none=False):
        """
        By default, set default value, remove undefined, remove none value

        set_default         if True, set the default value into the key
        remove_undefined    if True, remove all keys that are not defined
        allow_now           if False, all "None" value will be pop
        populate_none       if True, all keys that does not exist will be populate with None
        """
        for key, definition in cls._fields.items():
            if key not in document:
                if definition.default is not None and set_default:
                    document[key] = definition.get_default_value()
                elif populate_none:
                    document[key] = None
            else:
                if document.get(key) is None and not allow_none:
                    document.pop(key)
                elif isinstance(definition, DefinedDictField) and isinstance(document.get(key), dict):
                    definition.model.clean(document.get(key))
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
                if document.get(key, None) is None:
                    document[key] = value
                else:
                    definition = cls._fields.get(key)
                    if isinstance(definition, DefinedDictField):
                        definition.model.update(document.get(key), value)
                    elif isinstance(value, dict) and isinstance(document[key], dict):
                        document[key].update(value)
                    else:
                        document[key] = value

#################################### End of Defined Dict ####################################

