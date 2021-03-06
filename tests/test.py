#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from lxml import etree as ET

from hiccup import Hiccup, xfind, xfind_all
from hiccup import IfParentType, IfName

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


def as_xml(obj):
    return Hiccup().as_xml(obj)


class Xml:
    """
    Helper to aid comparing xmls
    """
    def __init__(self, xmls: str) -> None:
        self.xml = ET.fromstring(re.sub(r'\s', '', xmls, flags=re.MULTILINE))

    def __eq__(self, other: ET.ElementTree) -> bool:
        return Xml.elements_equal(self.xml, other)

    # based on https://stackoverflow.com/a/24349916/706389
    @staticmethod
    def elements_equal(e1, e2):
        def without_pyid(attrs):
            return {k: v for k, v in attrs.items() if k != '_python_id'}

        if e1.tag != e2.tag:
            return False
        if e1.text != e2.text:
            return False
        if e1.tail != e2.tail:
            return False
        if without_pyid(e1.attrib) != without_pyid(e2.attrib):
            return False
        if len(e1) != len(e2):
            return False

        ch1 = sorted(e1, key=lambda e: e.tag)
        ch2 = sorted(e2, key=lambda e: e.tag)
        return all(Xml.elements_equal(c1, c2) for c1, c2 in zip(ch1, ch2))


# TODO escaping??
# TODO ?? https://lxml.de/objectify.html#type-annotations
# TODO make sure root name is configurable??
def test_as_xml():
    assert as_xml('test') == Xml('<primitivish>test</primitivish>')
    assert as_xml(['first', 'second']) == Xml('''
<listish>
    <primitivish>first</primitivish>
    <primitivish>second</primitivish>
</listish>
    ''')


class Simple:
    def __init__(self, value) -> None:
        self.value = value

    @property
    def prop(self):
        return 'prop_' + self.value


def test_simple():
    xx = Simple('test')
    assert as_xml(xx) == Xml('''
<Simple>
  <value>test</value>
  <prop>prop_test</prop>
</Simple>
    ''')

    res = xfind(xx, '//value')
    assert res == 'test'


def test_simple_prop():
    xx = Simple('test')

    res = xfind(xx, '//prop')
    assert res == 'prop_test'


class Tree:
    def __init__(self, node: str, *children) -> None:
        self.node = node
        self.children = children


def test_tree():
    left = Tree('left')
    right = Tree('right')
    tt = Tree('aaa', left, right)
    assert as_xml(tt) == Xml('''
<Tree>
<node>aaa</node>
<children>
    <Tree><node>left</node><children></children></Tree>
    <Tree><node>right</node><children></children></Tree>
</children>
</Tree>
    ''')

    res = xfind(tt, '/Tree')
    assert res is tt

    resl = xfind_all(tt, '//Tree')
    assert len(resl) == 3
    # TODO not sure if we can generally control order...
    assert resl == [tt, left, right]


def test_types():
    class X:
        def __init__(self):
            self.first = 1
            self.second = 12.3
            self.third = False
            self.fourth = None

    x = X()
    as_xml(x)  # should not crash


def test_recursive():
    class X:
        def __init__(self):
            self.inf = None
    a = X()
    a.inf = a

    h = Hiccup()
    h.exclude(IfParentType(X), IfName('inf'))

    # should not crash
    h.as_xml(a)


def test_exclude_class():

    class A:
        def __init__(self):
            self.x = None
            self.b = None

    class B:
        def __init__(self):
            self.xxx = '123'

    a = A()
    a.x = 'value'
    a.b = B()

    h = Hiccup()
    # TODO fuck, this might be inconsistent...
    # why do we use b over B?
    # or maybe ok...
    assert h.as_xml(a) == Xml('''
<A>
    <x>value</x>
    <b>
        <xxx>123</xxx>
    </b>
</A>
    ''')

    h.exclude(IfParentType(B))

    assert h.as_xml(a) == Xml('''
<A>
    <x>value</x>
    <b>
    </b>
</A>
    ''')


def test_custom_primitive():
    from datetime import datetime
    d = datetime(year=2000, month=5, day=5)

    h = Hiccup()
    h.primitive_factory.converters[datetime] = lambda x: x.strftime('%Y%m%d%H:%M:%S')

    assert h.as_xml(d) == Xml('''
<primitivish>
2000050500:00:00
</primitivish>
    ''')


def test_name_mapping():
    class A:
        def __init__(self) -> None:
            pass
    ll = [
        A(),
        A(),
    ]

    h = Hiccup()
    h.type_name_map.maps[A] = 'new_name'

    assert h.as_xml(ll) == Xml('''
<listish>
    <new_name></new_name>
    <new_name></new_name>
</listish>
''')


def test_set_str():
    ss = {
        'aaa',
        'bbb',
        'ccc',
    }

    # shouldn't fail
    xfind(ss, "/listish/*[text()='aaa']")
    xfind(ss, "/listish/*[text()='bbb']")
    xfind(ss, "/listish/*[text()='ccc']")


def test_error():
    class A:
        @property
        def error(self):
            raise RuntimeError
    a = A()

    # shouldn't result in runtime error
    xfind_all(a, '//whatever')
    # TODO more reasonable error repr in xml??
    # TODO maybe warn via warnings module??


def test_bad_characters():
    sss = {
        "can behave di\x0berently",
    }

    res = xfind_all(sss, '//*[contains(text(), "behave")]')

    assert len(res) == 1


# TODO not sure... should that be configurable? going into all dictionaries might be pretty expensive
def test_query_dict():
    d = {
        'child': {
            'subchild': 'hello',
        }
    }

    res = xfind_all(d, '//child/subchild')

    assert len(res) == 1


# TODO ugh. maybe manually escape class names??
# this makes it pretty tricky though, since lxml code is C...
# ok, for now just skip it
# also xml word is reserved..
# for now test it doesn't crash
def test_bad_tag_filtered():
    class A:
        pass
    setattr(A, '<bad>', 'hello')

    a = A()
    as_xml(a)


def test_exclude_member():
    triggered = [False]

    class A:
        @property
        def do_not_include(self):
            triggered[0] = True
            return 1

        @property
        def include(self):
            return 'included'

    a = A()

    h = Hiccup()
    h.exclude(IfParentType(A), IfName('do_not_include'))
    assert h.xfind(a, '//include') == 'included'

    assert not triggered[0]
