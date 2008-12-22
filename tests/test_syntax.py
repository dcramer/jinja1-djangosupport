# -*- coding: utf-8 -*-
"""
    unit test for expression syntax
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: 2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from jinja import Environment, DictLoader
from jinja.exceptions import TemplateSyntaxError


CALL = '''{{ foo('a', c='d', e='f', *['b'], **{'g': 'h'}) }}'''
SLICING = '''{{ [1, 2, 3][:] }}|{{ [1, 2, 3][::-1] }}'''
ATTR = '''{{ foo.bar }}|{{ foo['bar'] }}'''
SUBSCRIPT = '''{{ foo[0] }}|{{ foo[-1] }}'''
KEYATTR = '''{{ {'items': 'foo'}.items }}|{{ {}.items() }}'''
TUPLE = '''{{ () }}|{{ (1,) }}|{{ (1, 2) }}'''
MATH = '''{{ (1 + 1 * 2) - 3 / 2 }}|{{ 2**3 }}'''
DIV = '''{{ 3 // 2 }}|{{ 3 / 2 }}|{{ 3 % 2 }}'''
UNARY = '''{{ +3 }}|{{ -3 }}'''
CONCAT = '''{{ [1, 2] ~ 'foo' }}'''
COMPARE = '''{{ 1 > 0 }}|{{ 1 >= 1 }}|{{ 2 < 3 }}|{{ 2 == 2 }}|{{ 1 <= 1 }}'''
INOP = '''{{ 1 in [1, 2, 3] }}|{{ 1 not in [1, 2, 3] }}'''
LITERALS = '''{{ [] }}|{{ {} }}|{{ () }}|{{ '' }}|{{ @() }}'''
BOOL = '''{{ true and false }}|{{ false or true }}|{{ not false }}'''
GROUPING = '''{{ (true and false) or (false and true) and not false }}'''
CONDEXPR = '''{{ 0 if true else 1 }}'''
DJANGOATTR = '''{{ [1, 2, 3].0 }}'''
FILTERPRIORITY = '''{{ "foo"|upper + "bar"|upper }}'''
REGEX = r'''{{ @/\S+/.findall('foo bar baz') }}'''
TUPLETEMPLATES = [
    '{{ () }}',
    '{{ (1, 2) }}',
    '{{ (1, 2,) }}',
    '{{ 1, }}',
    '{{ 1, 2 }}',
    '{% for foo, bar in seq %}...{% endfor %}',
    '{% for x in foo, bar %}...{% endfor %}',
    '{% for x in foo, %}...{% endfor %}',
    '{% for x in foo, recursive %}...{% endfor %}',
    '{% for x in foo, bar recursive %}...{% endfor %}',
    '{% for x, in foo, recursive %}...{% endfor %}'
]
TRAILINGCOMMA = '''{{ (1, 2,) }}|{{ [1, 2,] }}|{{ {1: 2,} }}|{{ @(1, 2,) }}'''


def test_call():
    from jinja import Environment
    env = Environment()
    env.globals['foo'] = lambda a, b, c, e, g: a + b + c + e + g
    tmpl = env.from_string(CALL)
    assert tmpl.render() == 'abdfh'


def test_slicing(env):
    tmpl = env.from_string(SLICING)
    assert tmpl.render() == '[1, 2, 3]|[3, 2, 1]'


def test_attr(env):
    tmpl = env.from_string(ATTR)
    assert tmpl.render(foo={'bar': 42}) == '42|42'


def test_subscript(env):
    tmpl = env.from_string(SUBSCRIPT)
    assert tmpl.render(foo=[0, 1, 2]) == '0|2'


def test_keyattr(env):
    tmpl = env.from_string(KEYATTR)
    assert tmpl.render() == 'foo|[]'


def test_tuple(env):
    tmpl = env.from_string(TUPLE)
    assert tmpl.render() == '()|(1,)|(1, 2)'


def test_math(env):
    tmpl = env.from_string(MATH)
    assert tmpl.render() == '1.5|8'


def test_div(env):
    tmpl = env.from_string(DIV)
    assert tmpl.render() == '1|1.5|1'


def test_unary(env):
    tmpl = env.from_string(UNARY)
    assert tmpl.render() == '3|-3'


def test_concat(env):
    tmpl = env.from_string(CONCAT)
    assert tmpl.render() == '[1, 2]foo'


def test_compare(env):
    tmpl = env.from_string(COMPARE)
    assert tmpl.render() == 'True|True|True|True|True'


def test_inop(env):
    tmpl = env.from_string(INOP)
    assert tmpl.render() == 'True|False'


def test_literals(env):
    tmpl = env.from_string(LITERALS)
    assert tmpl.render().lower() == '[]|{}|()||set([])'


def test_bool(env):
    tmpl = env.from_string(BOOL)
    assert tmpl.render() == 'False|True|True'


def test_grouping(env):
    tmpl = env.from_string(GROUPING)
    assert tmpl.render() == 'False'


def test_django_attr(env):
    tmpl = env.from_string(DJANGOATTR)
    assert tmpl.render() == '1'


def test_conditional_expression(env):
    tmpl = env.from_string(CONDEXPR)
    assert tmpl.render() == '0'


def test_filter_priority(env):
    tmpl = env.from_string(FILTERPRIORITY)
    assert tmpl.render() == 'FOOBAR'


def test_function_calls(env):
    tests = [
        (True, '*foo, bar'),
        (True, '*foo, *bar'),
        (True, '*foo, bar=42'),
        (True, '**foo, *bar'),
        (True, '**foo, bar'),
        (False, 'foo, bar'),
        (False, 'foo, bar=42'),
        (False, 'foo, bar=23, *args'),
        (False, 'a, b=c, *d, **e'),
        (False, '*foo, **bar')
    ]
    for should_fail, sig in tests:
        if should_fail:
            try:
                print env.from_string('{{ foo(%s) }}' % sig)
            except TemplateSyntaxError:
                continue
            assert False, 'expected syntax error'
        else:
            env.from_string('foo(%s)' % sig)


def test_regex(env):
    tmpl = env.from_string(REGEX)
    assert tmpl.render() == "['foo', 'bar', 'baz']"


def test_tuple_expr(env):
    for tmpl in TUPLETEMPLATES:
        assert env.from_string(tmpl)


def test_trailing_comma(env):
    tmpl = env.from_string(TRAILINGCOMMA)
    assert tmpl.render().lower() == '(1, 2)|[1, 2]|{1: 2}|set([1, 2])'


def test_extends_position():
    env = Environment(loader=DictLoader({
        'empty': '[{% block empty %}{% endblock %}]'
    }))
    tests = [
        ('{% extends "empty" %}', '[!]'),
        ('  {% extends "empty" %}', '[!]'),
        ('  !\n', '  !\n!'),
        ('{# foo #}  {% extends "empty" %}', '[!]'),
        ('{% set foo = "blub" %}{% extends "empty" %}', None)
    ]

    for tmpl, expected_output in tests:
        try:
            tmpl = env.from_string(tmpl + '{% block empty %}!{% endblock %}')
        except TemplateSyntaxError:
            assert expected_output is None, 'got syntax error'
        else:
            assert expected_output == tmpl.render()
