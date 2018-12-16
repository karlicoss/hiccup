# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = 'unknown'
finally:
    del get_distribution, DistributionNotFound


import inspect
from typing import Any, List, Dict

from lxml import etree as ET


class HikkupError(RuntimeError):
    pass



# TODO get instance of tree
# TODO apply adapter?
# TODO xquery on it

Xpath = str
Result = Any


# TODO should be configurable..
def is_primitive(obj):
    return isinstance(obj, (bool, int, float, str))

# TODO stringifyable? 
def is_dict_like(obj):
    return isinstance(obj, (dict))

def is_list_like(obj):
    return isinstance(obj, (list, tuple))

# TODO custom adapters?

def get_attributes(obj):
    res = inspect.getmembers(obj, lambda x: not any([inspect.ismethod(x), inspect.isfunction(x)]))
    return [(k, v) for k, v in res if not k.startswith('__')]

def get_name(obj):
    return type(obj).__name__

# TODO depending on instance, return??

_PY_ID = '_python_id'


def make_elem(obj, name: str) -> ET.Element:
    res = ET.Element(name)
    res.set(_PY_ID, str(id(obj)))
    return res

def as_xml(obj) -> ET.Element:
    if is_list_like(obj):
        res = make_elem(obj, 'listish')
        res.extend([as_xml(x) for x in obj])
        return res

    if is_primitive(obj):
        el = make_elem(obj, 'primitivish')
        el.text = obj # TODO to string??
        return el
    # TODO if has adapter, use that
    # otherwise, extract attributes...

    attrs = get_attributes(obj)

    res = make_elem(obj, get_name(obj))
    for k, v in attrs:
        oo = as_xml(v)
        # TODO what's key for??
        oo.tag = k
        ## TODO class attribute??
        res.append(oo)
        # TODO subelement might be necessary here??
        # TODO python id?
    return res

# TODO maintain a map?..
# TODO simple adapter which just maps properties and fields?
def xquery(obj, query: Xpath) -> List[Result]:
    xml = as_xml(obj)
    xelems = xml.xpath(query)
    py_ids = [int(x.attrib['_python_id']) for x in xelems]
    import ctypes
    return [ctypes.cast(py_id, ctypes.py_object).value for py_id in py_ids] # type: ignore


def xquery_single(obj: Any, query: Xpath) -> Result:
    res = xquery(obj, query)
    if len(res) != 1:
        raise HikkupError('{}: expected single result, got {} instead'.format(query, res))
    return res[0]

xfind = xquery_single
xfind_all = xquery

