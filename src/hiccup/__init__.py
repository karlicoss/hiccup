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
from typing import Any, List, Dict, Type, Optional, Set, Tuple, Callable

# pylint: disable=import-error
from lxml import etree as ET


def di(id_: int) -> Any:
    """
    Hacky inverse for id
    """
    return ctypes.cast(id_, ctypes.py_object).value # type: ignore


class HiccupError(RuntimeError):
    pass


# TODO apply adapter?

Xpath = str
Result = Any


def is_dict_like(obj):
    return isinstance(obj, (dict))

def is_list_like(obj):
    return isinstance(obj, (list, set, tuple))

AttrName = str

class Spec:
    def __init__(self, cls: Type[Any]) -> None:
        self._ignore = set() # type: Set[AttrName]
        self._ignore_all = False

    def ignore(self, attr: AttrName) -> None:
        self._ignore.add(attr)

    def ignore_all(self):
        self._ignore_all = True

    def ignored(self, attr: AttrName) -> bool:
        return self._ignore_all or attr in self._ignore


class TypeNameMap:
    def __init__(self) -> None:
        self.maps = {} # type: Dict[Type[Any], str]

    def get_type_name(self, obj: Any) -> str:
        tp = type(obj)
        res = self.maps.get(tp, None)
        if res is not None:
            return res

        return tp.__name__


class PrimitiveFactory:
    def as_primitive(self, obj: Any) -> Optional[str]:
        """
        None means non-primitive
        """
        raise NotImplementedError


class DefaultPrimitiveFactory(PrimitiveFactory):
    def __init__(self) -> None:
        self.converters = {
            type(None): lambda x: 'none',
            bool      : lambda x: 'true' if x else 'false',
            int       : lambda x: str(x),
            float     : lambda x: str(x),
            str       : lambda x: x,
        }

    def as_primitive(self, obj: Any) -> Optional[str]:
        conv = self.converters.get(type(obj), None)
        if conv is None:
            return None
        else:
            return conv(obj)

class Hiccup:
    def __init__(self) -> None:
        self._object_keeper = {} # type: Dict[int, Any]
        self._specs = {} # type: Dict[Type[Any], Spec]
        self.python_id_attr = '_python_id'
        self.primitive_factory = DefaultPrimitiveFactory()
        self.type_name_map = TypeNameMap()
        """
        Does some final rewriting of xml to query on
        """
        self.xml_hook = None # type: Optional[Callable[[ET], None]]

    def ignore(self, type_, attr: Optional[AttrName]=None) -> None:
        """
        If attr is None, ignore all of the calss attrs
        """
        sp = self._specs.get(type_, None)
        if sp is None:
            sp = Spec(type_)
            self._specs[type_] = sp
        if attr is None:
            sp.ignore_all()
        else:
            sp.ignore(attr)

    def take_member(self, m) -> bool:
        return not any([inspect.ismethod(m), inspect.isfunction(m)])

    def take_name(self, a: AttrName) -> bool:
        return not a.startswith('__')

    def get_attributes(self, obj: Any) -> List[Tuple[AttrName, Any]]:
        spec = self._specs.get(type(obj), None)
        res = inspect.getmembers(obj, self.take_member)
        return [(attr, v) for attr, v in res if self.take_name(attr) and not (spec is not None and spec.ignored(attr))]

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

    def _as_xmlstr(self, obj) -> str:
        return ET.tostring(self._as_xml(obj), pretty_print=True, encoding='unicode')

    def _as_xml(self, obj) -> ET.Element:
        if is_list_like(obj):
            res = self._make_elem(obj, 'listish')
            res.extend([self._as_xml(x) for x in obj])
            return res
        # TODO dict like

        prim = self.primitive_factory.as_primitive(obj)
        if prim is not None:
            el = self._make_elem(obj, 'primitivish')
            el.text = prim
            return el
        # TODO if has adapter, use that
        # otherwise, extract attributes...

        attrs = self.get_attributes(obj)

        res = self._make_elem(obj, self.type_name_map.get_type_name(obj))
        for k, v in attrs:
            oo = self._as_xml(v)
            oo.tag = k
            ## TODO class attribute??
            res.append(oo)
        return res

    def xquery(self, obj: Any, query: Xpath) -> List[Result]:
        xml = self._as_xml(obj)
        if self.xml_hook is not None:
            self.xml_hook(xml)

        xelems = xml.xpath(query)
        py_ids = [int(x.attrib[self.python_id_attr]) for x in xelems]
        return [di(py_id) for py_id in py_ids]

    def xquery_single(self, obj: Any, query: Xpath) -> Result:
       res = self.xquery(obj, query)
       if len(res) != 1:
           raise HiccupError('{}: expected single result, got {} instead'.format(query, res))
       return res[0]

    def xfind_all(self, *args, **kwargs):
        return self.xquery(*args, **kwargs)

    def xfind(self, *args, **kwargs):
        return self.xquery_single(*args, **kwargs)

# TODO simple adapter which just maps properties and fields?
def xquery(obj, query: Xpath, cls=Hiccup) -> List[Result]:
    return cls().xquery(obj=obj, query=query)

def xquery_single(obj: Any, query: Xpath, cls=Hiccup) -> Result:
    return cls().xquery_single(obj=obj, query=query)

xfind = xquery_single
xfind_all = xquery

