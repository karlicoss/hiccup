#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pytest

from lxml import etree as ET

import hikkup
from hikkup import as_xml

__author__ = "Dima Gerasimov"
__copyright__ = "Dima Gerasimov"
__license__ = "mit"


class Tree:
    def __init__(self, node: str, *children) -> None:
        self.node = node
        self.children = children


class Simple:
    def __init__(self, value) -> None:
        self.value = value

    @property
    def prop(self):
        return self.value


class Xml:
    def __init__(self, xmls: str):
        self.xml = ET.fromstring(re.sub('\s', '', xmls, flags=re.MULTILINE))

    def __eq__(self, other):
        return Xml.elements_equal(self.xml, other)

    # https://stackoverflow.com/a/24349916/706389
    @staticmethod
    def elements_equal(e1, e2):
        if e1.tag != e2.tag: return False
        if e1.text != e2.text: return False
        if e1.tail != e2.tail: return False
        if e1.attrib != e2.attrib: return False
        if len(e1) != len(e2): return False

        ch1 = sorted(e1, key=lambda e: e.tag)
        ch2 = sorted(e2, key=lambda e: e.tag)
        return all(Xml.elements_equal(c1, c2) for c1, c2 in zip(ch1, ch2))

def fwf_test_as_xml():
    # TODO implicit root??
    assert as_xml('test') == Xml('test')
    # TODO ???
    # TODO implicit indices?
    # TODO make sure root name is configurable??
    # TODO escaping??
    # TODO ?? https://lxml.de/objectify.html#type-annotations
    assert as_xml(['first', 'second']) == Xml('''
<root>
    <0>first</0>
    <1>second</1>
</root>
    ''')


def test_simple():
    xx = Simple('test')
    # TODO map class name?
    assert as_xml(xx) == Xml('''
<Simple>
  <value>test</value>
  <prop>test</prop>
</Simple>
    ''')


def qqq_test_tree():
    tt = Tree('aaa', Tree('left'), Tree('right'))
    # TODO not sure if indices are a good idea?
    assert as_xml(tt) == Xml('''
<Tree>
<node>aaa</node>
<children>
    <Tree><node>left</node><children></children></Tree>
    <Tree><node>right</node><children></children></Tree>
</children>
</Tree>

    ''')
