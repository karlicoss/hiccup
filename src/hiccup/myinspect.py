from inspect import getmro, isclass
from typing import Set
import types
"""
a copy of inspect.getmembers but capable of error handling
TODO maybe, commit it to python? could it be useful??
"""

_inprogress = object()

class InspectError(RuntimeError):
    pass


def getmembers(object, path, excluded):
    """Return all members of an object as (name, value) pairs sorted by name.
    Optionally, only return members that satisfy a given predicate."""
    if isclass(object):
        mro = (object,) + getmro(object)
    else:
        mro = ()
    results = []
    processed = set() # type: Set[str]
    names = dir(object)
    # :dd any DynamicClassAttributes to the list of names if object is a class;
    # this may result in duplicate entries if, for example, a virtual
    # attribute with the same name as a DynamicClassAttribute exists
    try:
        for base in object.__bases__:
            for k, v in base.__dict__.items():
                if isinstance(v, types.DynamicClassAttribute):
                    names.append(k)
    except AttributeError:
        pass
    for key in names:
        if excluded(path + [(key, _inprogress)]):
            continue
        # First try to get the value via getattr.  Some descriptors don't
        # like calling their __get__ (see bug #1785), so fall back to
        # looking in the __dict__.
        try:
            value = getattr(object, key)
            # handle the duplicate key
            if key in processed:
                raise AttributeError
        except AttributeError:
            for base in mro:
                if key in base.__dict__:
                    value = base.__dict__[key]
                    break
            else:
                # could be a (currently) missing slot member, or a buggy
                # __dir__; discard and move on
                continue
        except Exception as ex:
            # TODO ugh, is there an easier way of setting cause???
            try:
                raise InspectError from ex
            except InspectError as ie:
                value = ie
        if isinstance(value, InspectError) or not excluded(path + [(key, value)]):
            results.append((key, value))
        processed.add(key)
    results.sort(key=lambda pair: pair[0])
    return results
