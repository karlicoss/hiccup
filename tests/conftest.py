#!/usr/bin/env python3

import pytest

from lxml import etree as ET

def pretty(xml):
    return ET.tostring(xml, pretty_print=True, encoding='unicode').splitlines()

def pytest_assertrepr_compare(op, left, right):
    from test import Xml
    if isinstance(right, Xml) and op == "==":
        return ['Comparing xmls:',
                '  left:', *['    ' + x for x in pretty(left)], '  right:', *['    ' + x for x in pretty(right.xml)]]
