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
AttrName = str
Context = List[Tuple[Optional[AttrName], Any]] # 'path' to the object, including itself
Result = Any

Check = Callable[[Context], bool]

def IfType(cls: Type[Any]) -> Check:
    def check(ctx):
        me = ctx[-1]
        return type(me[1]) == cls
    return check

def IfParentType(cls: Type[Any]) -> Check:
    def check(ctx):
        if len(ctx) < 2:
            return False
        p = ctx[-2]
        return type(p[1]) == cls
    return check

def IfName(name: AttrName) -> Check:
    def check(ctx):
        p = ctx[-1]
        return p[0] == name
    return check


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

def is_dict_like(obj):
    return isinstance(obj, (dict))

def is_list_like(obj):
    return isinstance(obj, (list, set, tuple))

class Hiccup:
    def __init__(self) -> None:
        self._object_keeper = {} # type: Dict[int, Any]
        self._exclude = [] # type: List[Tuple[Check]]
        self.python_id_attr = '_python_id'
        self.primitive_factory = DefaultPrimitiveFactory()
        self.type_name_map = TypeNameMap()
        """
        Does some final rewriting of xml to query on
        """
        self.xml_hook = None # type: Optional[Callable[[ET], None]]

    def exclude(self, *conditions) -> None:
        """
        Excludes the thing respecting all of these predicates from xml converstion. Helpful to eliminate recursion.
        """
        self._exclude.append(conditions) # type: ignore

    def take_member(self, m: Any) -> bool:
        return not any([inspect.ismethod(m), inspect.isfunction(m)])

    def take_name(self, a: AttrName) -> bool:
        return not a.startswith('__')

    def get_attributes(self, obj: Any) -> List[Tuple[AttrName, Any]]:
        # TODO shit. inspect may result in exception even though we weren't intending to looking at the value :(
        res = inspect.getmembers(obj, self.take_member)
        return [(attr, v) for attr, v in res if self.take_name(attr)]

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
        return ET.tostring(self.as_xml(obj), pretty_print=True, encoding='unicode')

    def _is_excluded(self, ctx: Context) -> bool:
        for ll in self._exclude:
            if all([l(ctx) for l in ll]):
                return True
        return False

    def _as_xml(self, ctx: Context) -> Optional[ET.Element]:
        if self._is_excluded(ctx):
            return None
        name, obj = ctx[-1]

        if is_list_like(obj):
            res = self._make_elem(obj, 'listish')
            for x in obj:
                ctx.append((None, x))
                rr = self._as_xml(ctx)
                ctx.pop()
                if rr is not None:
                    res.append(rr)
            return res

        prim = self.primitive_factory.as_primitive(obj)
        if prim is not None:
            el = self._make_elem(obj, 'primitivish')
            el.text = prim
            return el

        attrs = self.get_attributes(obj)

        # TODO dict like
        res = self._make_elem(obj, self.type_name_map.get_type_name(obj))
        for k, v in attrs:
            ctx.append((k, v))
            oo = self._as_xml(ctx)
            ctx.pop()
            if oo is not None:
                oo.tag = k
                ## TODO class attribute??
                res.append(oo)
        return res

    def as_xml(self, obj: Any) -> Optional[ET.Element]:
        return self._as_xml([(None, obj)])

    def xquery(self, obj: Any, query: Xpath) -> List[Result]:
        xml = self.as_xml(obj)
        assert xml is not None

        if self.xml_hook is not None:
            # pylint: disable=not-callable
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

def xquery(obj, query: Xpath, cls=Hiccup) -> List[Result]:
    return cls().xquery(obj=obj, query=query)

def xquery_single(obj: Any, query: Xpath, cls=Hiccup) -> Result:
    return cls().xquery_single(obj=obj, query=query)

xfind = xquery_single
xfind_all = xquery

