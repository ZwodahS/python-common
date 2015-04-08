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

from .defined_dict import *

class CleanerMixin(Mixin):
    """
    Cleaner mixin allows you to specify a label and allow you to run a "clean_label" method
    to clean inclusive/exclusive fields
    """

    @classmethod
    def _apply_mixin(cls, new_cls, name, bases, cdict):
        for key, definition in new_cls._fields.items():
            if hasattr(definition, "labels"):
                if isinstance(definition.labels, str):
                    definition.labels = set([definition.labels])
                if not isinstance(definition.labels, set):
                    definition.labels = set(definition.labels)

    @classmethod
    def clean_labels(cls, document, labels, exclude=None):
        exclude = exclude or set()
        if exclude is not None and isinstance(exclude, str):
            exclude = (exclude, )
        if isinstance(labels, str):
            labels = (labels, )
        labels = set(labels)
        exclude = set(exclude)

        for key, definition in cls._fields.items():
            if key in document and hasattr(definition, "labels"):
                if ((labels is None and len(definition.labels) > 0) or (len(labels & definition.labels) > 0)) and len(definition.labels & exclude) == 0:
                    document.pop(key)
            if isinstance(definition, DefinedDictField) and document.get(key) is not None and CleanerMixin in definition.model._mixins:
                definition.model.clean_labels(document.get(key), labels, exclude=exclude)

