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

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


import inspect
import ctypes
from typing import Any, List, Dict

# pylint: disable=import-error
from lxml import etree as ET


def di(id_: int) -> Any:
    """
    Hacky inverse for id
    """
    return ctypes.cast(id_, ctypes.py_object).value # type: ignore


class HikkupError(RuntimeError):
    pass


# TODO apply adapter?

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

def get_attributes(obj: Any):
    res = inspect.getmembers(obj, lambda x: not any([inspect.ismethod(x), inspect.isfunction(x)]))
    return [(k, v) for k, v in res if not k.startswith('__')]

def get_name(obj: Any):
    return type(obj).__name__

class Hikkup:
    def __init__(self) -> None:
        self._object_keeper = {} # type: Dict[int, Any]
        self.python_id_attr = '_python_id'

    def _keep(self, obj: Any):
        """
        Necessary to prevent temporaries from being GC'ed while querying
        """
        self._object_keeper[id(obj)] = obj

    def _make_elem(self, obj: Any, name: str) -> ET.Element:
        res = ET.Element(name)
        self._keep(obj)
        res.set(self.python_id_attr, str(id(obj)))
        return res

    def _as_xml(self, obj) -> ET.Element:
        if is_list_like(obj):
            res = self._make_elem(obj, 'listish')
            res.extend([self._as_xml(x) for x in obj])
            return res

        if is_primitive(obj):
            el = self._make_elem(obj, 'primitivish')
            el.text = obj # TODO to string??
            return el
        # TODO if has adapter, use that
        # otherwise, extract attributes...

        attrs = get_attributes(obj)

        res = self._make_elem(obj, get_name(obj))
        for k, v in attrs:
            oo = self._as_xml(v)
            oo.tag = k
            ## TODO class attribute??
            res.append(oo)
        return res

    def xquery(self, obj: Any, query: Xpath) -> List[Result]:
        xml = self._as_xml(obj)
        xelems = xml.xpath(query)
        py_ids = [int(x.attrib[self.python_id_attr]) for x in xelems]
        return [di(py_id) for py_id in py_ids]

    def xquery_single(self, obj: Any, query: Xpath) -> Result:
       res = self.xquery(obj, query)
       if len(res) != 1:
           raise HikkupError('{}: expected single result, got {} instead'.format(query, res))
       return res[0]

# TODO simple adapter which just maps properties and fields?
def xquery(obj, query: Xpath, cls=Hikkup) -> List[Result]:
    return cls().xquery(obj=obj, query=query)

def xquery_single(obj: Any, query: Xpath, cls=Hikkup) -> Result:
    return cls().xquery_single(obj=obj, query=query)

xfind = xquery_single
xfind_all = xquery

