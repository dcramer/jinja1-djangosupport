# -*- coding: utf-8 -*-
"""
    jinja.contrib._djangosupport
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2007 by Armin Ronacher, Bryan McLemore, David Cramer.
    :license: BSD, see LICENSE for more details.
"""
from _djangosupport import *

def setup_django_module():
    """
    create a new Jinja module for django.
    """
    import new
    import sys
    
    from django import contrib
    from jinja.contrib import _djangosupport
    
    module = contrib.jinja = sys.modules['django.contrib.jinja'] = \
             new.module('django.contrib.jinja')
    module.__doc__ = _djangosupport.__doc__
    module.__all__ = _djangosupport.__all__
    get_name = globals().get
    for name in _djangosupport.__all__:
        setattr(module, name, get_name(name))

def configure(*args, **kwargs):
    import warnings

    warnings.warn("Magical configuration has been Deprecated. Please use jinja.contrib.djangosupport for imports.", DeprecationWarning)
    setup_django_module()