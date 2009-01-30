# -*- coding: utf-8 -*-
"""
    jinja.contrib.djangosupport
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Support for the django framework.

    Rendering Templates
    ===================

    To render a template you can use the functions `render_to_string` or
    `render_to_response` from the `jinja.contrib.djangosupport` module::

        from jinja.contrib.djangosupport import render_to_response
        resp = render_to_response('Hello {{ username }}!', {
            'username':     req.session['username']
        }, req)

    `render_to_string` and `render_to_response` take at least the name of
    the template as argument, then the optional dict which will become the
    context.  If you also provide a request object as third argument the
    context processors will be applied.

    `render_to_response` also takes a forth parameter which can be the
    content type which defaults to `DEFAULT_CONTENT_TYPE`.

    Generic Views
    =============
    
    Some generic views in Django render templates, and thus they no longer work with Jinja's
    template handler. The first of which are included, are error page handlers.
    To use these, simply place two lines in your `urls.py` file::
    
        handler404 = 'jinja.contrib.djangosupport.handler404'
        handler500 = 'jinja.contrib.djangosupport.handler500'
        
    Also included is a replacement for the `direct_to_template` generic view.
    
        (r'^robots\.txt$', 'jinja.contrib.djangosupport.direct_to_template', {'template': 'robots.txt'}),

    Converting Filters
    ==================

    One of the useful objects provided by `jinja.contrib.djangosupport` is the
    `register` object which can be used to register filters, tests and
    global objects.  You can also convert any filter django provides in
    a Jinja filter using `convert_django_filter`::

        from jinja.contrib.djangosupport import register, convert_django_filter
        from django.template.defaultfilters import floatformat

        register.filter(convert_django_filter(floatformat), 'floatformat')

    Available methods on the `register` object:

    ``object (obj[, name])``
        Register a new global as name or with the object's name.
        Returns the function object unchanged so that you can use
        it as decorator if no name is provided.

    ``filter (func[, name])``
        Register a function as filter with the name provided or
        the object's name as filtername.
        Returns the function object unchanged so that you can use
        it as decorator if no name is provided.

    ``test (func[, name])``
        Register a function as test with the name provided or the
        object's name as testname.
        Returns the function object unchanged so that you can use
        it as decorator if no name is provided.

    ``context_inclusion (func, template[, name])``
        Register a function with a name provided or the func object's
        name in the global namespace that acts as subrender function.

        func is called with the callers context as dict and the
        arguments and keywords argument of the inclusion function.
        The function should then process the context and return a
        new context or the same context object. Afterwards the
        template is rendered with this context.

        Example::

            def add_author(context, author=None):
                if author is not None:
                    author = Author.objects.get(name=author)
                context['author'] = author
                return context

            register.context_inclusion(add_author, 'author_details.html',
                                       'render_author_details')

        You can use it in the template like this then::

            {{ render_author_details('John Doe') }}

    ``clean_inclusion (func, template[, name[, run_processors]]) ``
        Works like `context_inclusion` but doesn't use the calles
        context but an empty context. If `run_processors` is `True`
        it will lookup the context for a `request` object and pass
        it to the render function to apply context processors.

    :copyright: 2007 by Armin Ronacher, Bryan McLemore, David Cramer.
    :license: BSD, see LICENSE for more details.
"""
try:
    __import__('django')
except ImportError:
    raise ImportError('installed django required for djangosupport')

import sys
import warnings
from django.template.context import get_standard_processors
from django.http import HttpResponse
from django.conf import settings

from jinja import Environment, FileSystemLoader, ChoiceLoader
from jinja.loaders import MemcachedFileSystemLoader

__all__ = ('render_to_response', 'render_to_string', 'convert_django_filter', 'handler404', 'handler500', 'direct_to_template', 'env', 'register')

#: used environment
env = None

#: default filters
DEFAULT_FILTERS = (
    'django.template.defaultfilters.date',
    'django.template.defaultfilters.timesince',
    'django.template.defaultfilters.linebreaks',
    'django.contrib.humanize.templatetags.humanize.intcomma'
)

def configure(convert_filters=DEFAULT_FILTERS, loader=None, **options):
    """
    Initialize the system.
    """
    global env

    if env:
        warnings.warn("Jinja already initialized.")
        return

    # setup environment
    if loader is None:
        loaders = tuple(FileSystemLoader(l) for l in settings.TEMPLATE_DIRS)
        if not loaders:
            loader = None
        elif len(loaders) == 1:
            loader = loaders[0]
        else:
            loader = ChoiceLoader(loaders)
    env = Environment(loader=loader, **options)

    # convert requested filters
    for name in convert_filters:
        env.filters[name] = convert_django_filter(name)

    # import templatetags of installed apps
    for app in settings.INSTALLED_APPS:
        try:
            __import__(app + '.templatetags')
        except ImportError:
            pass

def render_to_response(template, context={}, request=None,
                       mimetype=None):
    """This function will take a few variables and spit out a full webpage."""
    content = render_to_string(template, context, request)
    if mimetype is None:
        mimetype = settings.DEFAULT_CONTENT_TYPE
    return HttpResponse(content, mimetype)


def render_to_string(template, context={}, request=None):
    """Render a template to a string."""
    assert env is not None, 'Jinja not configured for django'
    if request is not None:
        # It's very important to apply these in a specific order
        default_context = {
            'request': request,
        }
        for processor in get_standard_processors():
            default_context.update(processor(request))
        default_context.update(context)
        context = default_context
    template = env.get_template(template)
    return template.render(context)


def convert_django_filter(f):
    """Convert a django filter into a Jinja filter."""
    if isinstance(f, str):
        p = f.split('.')
        f = getattr(__import__('.'.join(p[:-1]), None, None, ['']), p[-1])
    def filter_factory(*args):
        def wrapped(env, ctx, value):
            return f(value, *args)
        return wrapped
    filter_factory.__name__ = f.__name__
    filter_factory.__doc__ = getattr(f, '__doc__', None)
    return filter_factory


class Library(object):
    """
    Continues a general feel of wrapping all the registration
    methods for easy importing.

    This is available in `jinja.contrib.djangosupport` as `register`.

    For more details see the docstring of the `jinja.contrib.djangosupport` module.
    """
    def object(func, name=None):
        """Register a new global."""
        if name is None:
            name = getattr(func, '__name__')
        env.globals[name] = func
        return func
    object = staticmethod(object)

    def filter(func, name=None):
        """Register a new filter function."""
        if name is None:
            name = func.__name__
        env.filters[name] = func
        return func
    filter = staticmethod(filter)

    def test(func, name):
        """Register a new test function."""
        if name is None:
            name = func.__name__
        env.tests[name] = func
        return func
    test = staticmethod(test)

    def context_inclusion(func, template, name=None):
        """
        Similar to the inclusion tag from django this one expects func to be a
        function with a similar argument list to func(context, *args, **kwargs)

        It passed in the current context allowing the function to edit it or read
        from it.  the function must return a dict with which to pass into the
        renderer.  Normally expected is an altered dictionary.

        Note processors are NOT ran on this context.
        """
        def wrapper(env, context, *args, **kwargs):
            context = func(context.to_dict(), *args, **kwargs)
            return render_to_string(template, context)
        wrapper.jinja_context_callable = True
        if name is None:
            name = func.__name__
        try:
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
        except:
            pass
        env.globals[name] = wrapper
    context_inclusion = staticmethod(context_inclusion)

    def clean_inclusion(func, template, name=None, run_processors=False):
        """
        Similar to above however it won't pass the context into func().
        Also the returned context will have the context processors run upon it.
        """
        def wrapper(env, context, *args, **kwargs):
            if run_processors:
                request = context['request']
            else:
                request = None
            context = func({}, *args, **kwargs)
            return render_to_string(template, context, request)
        wrapper.jinja_context_callable = True
        if name is None:
            name = func.__name__
        try:
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
        except:
            pass
        env.globals[name] = wrapper
    clean_inclusion = staticmethod(clean_inclusion)
register = Library

def handler404(request):
    """404 error handler."""
    response = render_to_response('404.html', {}, request)
    response.status_code = 404
    return response

def handler500(request):
    """500 error handler."""
    response = render_to_response('500.html', {}, request)
    response.status_code = 500
    return response

def direct_to_template(request, template):
    """Generic template direction view."""
    return render_to_response(template, {}, request)

if not env:
    configure()