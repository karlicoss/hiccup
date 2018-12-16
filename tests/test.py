#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pytest

from lxml import etree as ET

import hikkup
from hikkup import as_xml, xquery, xfind, xfind_all

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"

class Xml:
    """
    Helper to aid comparing xmls
    """
    def __init__(self, xmls: str) -> None:
        self.xml = ET.fromstring(re.sub('\s', '', xmls, flags=re.MULTILINE))

    def __eq__(self, other: ET.ElementTree) -> bool:
        return Xml.elements_equal(self.xml, other)

    # based on https://stackoverflow.com/a/24349916/706389
    @staticmethod
    def elements_equal(e1, e2):
        def without_pyid(attrs):
            return {k: v for k, v in attrs.items() if k != '_python_id'}

        if e1.tag != e2.tag: return False
        if e1.text != e2.text: return False
        if e1.tail != e2.tail: return False
        if without_pyid(e1.attrib) != without_pyid(e2.attrib): return False
        if len(e1) != len(e2): return False

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


@pytest.mark.skip(reason="properties are broken presumably because they are returning temporaries")
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
