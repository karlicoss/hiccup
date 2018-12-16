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



# TODO get instance of tree
# TODO apply adapter?
# TODO xquery on it

Xpath = str

from lxml import etree as ET


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

def as_xml(obj) -> ET.Element:
    if is_list_like(obj):
        res = ET.Element('listish')
        res.extend([as_xml(x) for x in obj])
        return res

    if is_primitive(obj):
        el = ET.Element('primitivish')
        el.text = obj # TODO to string??
        return el
    # TODO if has adapter, use that
    # otherwise, extract attributes...

    attrs = get_attributes(obj)

    # ee = ET.Element('root' if self.parent is None else 'org')
    res = ET.Element(get_name(obj))
    for k, v in attrs:
        oo = as_xml(v)
        # TODO what's key for??
        oo.tag = k
        ## TODO class attribute??
        res.append(oo)
        # TODO subelement might be necessary here??
        # TODO python id?
    return res

def xquery(obj, query: str):
    # TODO simple adapter which just maps properties and fields?
    pass
