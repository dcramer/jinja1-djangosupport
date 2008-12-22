# -*- coding: utf-8 -*-
"""
    jinja.debugger
    ~~~~~~~~~~~~~~

    This module implements helper function Jinja uses to give the users a
    possibility to develop Jinja templates like they would debug python code.
    It seamlessly integreates into the python traceback system, in fact it
    just modifies the trackback stack so that the line numbers are correct
    and the frame information are bound to the context and not the frame of
    the template evaluation loop.

    To achive this it raises the exception it cought before in an isolated
    namespace at a given line. The locals namespace is set to the current
    template context.

    The traceback generated by raising that exception is then either returned
    or linked with the former traceback if the `jinja._debugger` module is
    available. Because it's not possible to modify traceback objects from the
    python space this module is needed for this process.

    If it's not available it just ignores the other frames. Because this can
    lead to actually harder to debug code there is a setting on the jinja
    environment to disable the debugging system.

    The isolated namespace which is used to raise the exception also contains
    a `__loader__` name that holds a reference to a PEP 302 compatible loader.
    Because there are currently some traceback systems (such as the paste
    evalexception debugger) that do not provide the frame globals when
    retrieving the source from the linecache module, Jinja injects the source
    to the linecache module itself and changes the filename to a URL style
    "virtual filename" so that Jinja doesn't acidentally override other files
    in the linecache.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""

import sys
from random import randrange

# if we have extended debugger support we should really use it
try:
    from jinja._debugger import *
    has_extended_debugger = True
except ImportError:
    has_extended_debugger = False

# we need the RUNTIME_EXCEPTION_OFFSET to skip the not used frames
from jinja.utils import reversed, RUNTIME_EXCEPTION_OFFSET


def fake_template_exception(exc_type, exc_value, tb, filename, lineno,
                            source, context_or_env, tb_back=None):
    """
    Raise an exception "in a template". Return a traceback
    object. This is used for runtime debugging, not compile time.
    """
    # some traceback systems allow to skip frames
    __traceback_hide__ = True

    # create the namespace which will be the local namespace
    # of the new frame then. Some debuggers show local variables
    # so we better inject the context and not the evaluation loop context.
    from jinja.datastructure import Context
    if isinstance(context_or_env, Context):
        env = context_or_env.environment
        namespace = context_or_env.to_dict()
    else:
        env = context_or_env
        namespace = {}

    # no unicode for filenames
    if isinstance(filename, unicode):
        filename = filename.encode('utf-8')

    # generate an jinja unique filename used so that linecache
    # gets data that doesn't interfere with other modules
    if filename is None:
        vfilename = 'jinja://~%d' % randrange(0, 10000)
        filename = '<string>'
    else:
        vfilename = 'jinja://%s' % filename

    # now create the used loaded and update the linecache
    loader = TracebackLoader(env, source, filename)
    loader.update_linecache(vfilename)
    globals = {
        '__name__':                 vfilename,
        '__file__':                 vfilename,
        '__loader__':               loader
    }

    # use the simple debugger to reraise the exception in the
    # line where the error originally occoured
    globals['__exception_to_raise__'] = (exc_type, exc_value)
    offset = '\n' * (lineno - 1)
    code = compile(offset + 'raise __exception_to_raise__[0], '
                            '__exception_to_raise__[1]',
                   vfilename or '<template>', 'exec')
    try:
        exec code in globals, namespace
    except:
        exc_info = sys.exc_info()

    # if we have an extended debugger we set the tb_next flag so that
    # we don't loose the higher stack items.
    if has_extended_debugger:
        if tb_back is not None:
            tb_set_next(tb_back, exc_info[2])
        if tb is not None:
            tb_set_next(exc_info[2].tb_next, tb.tb_next)

    # otherwise just return the exc_info from the simple debugger
    return exc_info


def translate_exception(template, context, exc_type, exc_value, tb):
    """
    Translate an exception and return the new traceback.
    """
    # depending on the python version we have to skip some frames to
    # step to get the frame of the current template. The frames before
    # are the toolchain used to render that thing.
    for x in xrange(RUNTIME_EXCEPTION_OFFSET):
        tb = tb.tb_next

    result_tb = prev_tb = None
    initial_tb = tb

    # translate all the jinja frames in this traceback
    while tb is not None:
        if tb.tb_frame.f_globals.get('__jinja_template__'):
            debug_info = tb.tb_frame.f_globals['debug_info']

            # the next thing we do is matching the current error line against the
            # debugging table to get the correct source line. If we can't find the
            # filename and line number we return the traceback object unaltered.
            error_line = tb.tb_lineno
            for code_line, tmpl_filename, tmpl_line in reversed(debug_info):
                if code_line <= error_line:
                    source = tb.tb_frame.f_globals['template_source']
                    tb = fake_template_exception(exc_type, exc_value, tb,
                                                 tmpl_filename, tmpl_line,
                                                 source, context, prev_tb)[-1]
                    break
        if result_tb is None:
            result_tb = tb
        prev_tb = tb
        tb = tb.tb_next

    # under some conditions we cannot translate any frame. in that
    # situation just return the original traceback.
    return (exc_type, exc_value, result_tb or intial_tb)


def raise_syntax_error(exception, env, source=None):
    """
    This method raises an exception that includes more debugging
    informations so that debugging works better. Unlike
    `translate_exception` this method raises the exception with
    the traceback.
    """
    exc_info = fake_template_exception(exception, None, None,
                                       exception.filename,
                                       exception.lineno, source, env)
    raise exc_info[0], exc_info[1], exc_info[2]


class TracebackLoader(object):
    """
    Fake importer that just returns the source of a template. It's just used
    by Jinja interally and you shouldn't use it on your own.
    """

    def __init__(self, environment, source, filename):
        self.loader = environment.loader
        self.source = source
        self.filename = filename

    def update_linecache(self, virtual_filename):
        """
        Hacky way to let traceback systems know about the
        Jinja template sourcecode. Very hackish indeed.
        """
        # check for linecache, not every implementation of python
        # might have such an module (this check is pretty senseless
        # because we depend on cpython anway)
        try:
            from linecache import cache
        except ImportError:
            return
        data = self.get_source(None)
        cache[virtual_filename] = (
            len(data),
            None,
            data.splitlines(True),
            virtual_filename
        )

    def get_source(self, impname):
        """Return the source as bytestring."""
        source = ''
        if self.source is not None:
            source = self.source
        elif self.loader is not None:
            try:
                source = self.loader.get_source(self.filename)
            except TemplateNotFound:
                pass
        if isinstance(source, unicode):
            source = source.encode('utf-8')
        return source
