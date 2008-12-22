# -*- coding: utf-8 -*-
"""
    unit test for the inheritance
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from jinja import Environment, DictLoader
from jinja.exceptions import TemplateSyntaxError

LAYOUTTEMPLATE = '''\
|{% block block1 %}block 1 from layout{% endblock %}
|{% block block2 %}block 2 from layout{% endblock %}
|{% block block3 %}
{% block block4 %}nested block 4 from layout{% endblock %}
{% endblock %}|'''

LEVEL1TEMPLATE = '''\
{% extends "layout" %}
{% block block1 %}block 1 from level1{% endblock %}'''

LEVEL2TEMPLATE = '''\
{% extends "level1" %}
{% block block2 %}{% block block5 %}nested block 5 from level2{%
endblock %}{% endblock %}'''

LEVEL3TEMPLATE = '''\
{% extends "level2" %}
{% block block5 %}block 5 from level3{% endblock %}
{% block block4 %}block 4 from level3{% endblock %}
'''

LEVEL4TEMPLATE = '''\
{% extends "level3" %}
{% block block3 %}block 3 from level4{% endblock %}
'''

BROKENTEMPLATE = '''\
{% extends "layout" %}
{% if false %}
  {% block block1 %}
    this is broken
  {% endblock %}
{% endif %}
'''

WORKINGTEMPLATE = '''\
{% extends "layout" %}
{% block block1 %}
  {% if false %}
    {% block block2 %}
      this should workd
    {% endblock %}
  {% endif %}
{% endblock %}
'''

def test_layout(env):
    tmpl = env.get_template('layout')
    assert tmpl.render() == ('|block 1 from layout|block 2 from '
                             'layout|nested block 4 from layout|')


def test_level1(env):
    tmpl = env.get_template('level1')
    assert tmpl.render() == ('|block 1 from level1|block 2 from '
                             'layout|nested block 4 from layout|')


def test_level2(env):
    tmpl = env.get_template('level2')
    assert tmpl.render() == ('|block 1 from level1|nested block 5 from '
                             'level2|nested block 4 from layout|')


def test_level3(env):
    tmpl = env.get_template('level3')
    assert tmpl.render() == ('|block 1 from level1|block 5 from level3|'
                             'block 4 from level3|')


def test_level4(env):
    tmpl = env.get_template('level4')
    assert tmpl.render() == ('|block 1 from level1|block 5 from '
                             'level3|block 3 from level4|')


def test_super():
    env = Environment(loader=DictLoader({
        'a': '{% block intro %}INTRO{% endblock %}|'
             'BEFORE|{% block data %}INNER{% endblock %}|AFTER',
        'b': '{% extends "a" %}{% block data %}({{ '
             'super() }}){% endblock %}',
        'c': '{% extends "b" %}{% block intro %}--{{ '
             'super() }}--{% endblock %}\n{% block data '
             '%}[{{ super() }}]{% endblock %}'
    }))
    tmpl = env.get_template('c')
    assert tmpl.render() == '--INTRO--|BEFORE|[(INNER)]|AFTER'


def test_broken(env):
    try:
        tmpl = env.get_template('broken')
    except TemplateSyntaxError:
        pass
    else:
        raise RuntimeError('no syntax error occured')


def test_working(env):
    tmpl = env.get_template('working')


def test_shortcut(env):
    tmpl = env.from_string('{% block foo "42" %}')
    assert tmpl.render() == '42'


def test_empty_super():
    env = Environment(loader=DictLoader({'a': '{% block foo %}{% endblock %}'}))
    t = env.from_string('{% extends "a" %}{% block foo %}{{ super() }}{% endblock %}')
    assert t.render() == ''
