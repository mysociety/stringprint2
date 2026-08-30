'''
Created on 26 Mar 2016

@author: alex
'''

from django.shortcuts import render
from django.http.response import HttpResponse
from django.shortcuts import HttpResponseRedirect
from .exceptions import RedirectException

try:
    from useful_inkleby.decorators import GenericDecorator
except:
    from ..decorators import GenericDecorator


def handle_redirect(func):

    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RedirectException as new_url:
            return HttpResponseRedirect(str(new_url))

    return inner


class FunctionalView(object):
    """
    Very simple class-based view that simple expects the class to have a 
    'template' variable and a 'view' function that expects (self, request). 

    Idea is to preserve cleanness of functional view logic but tidy up the 
    most common operation. 

    """

    template = ""
    require_staff = False
    require_login = False
    view_decorators = []

    @classmethod
    def as_view(cls, decorators=True):
        """
        if decorators is True - we apply any view_decorators listed for the class
        if no_auth = True, we bypass staff and user testing(useful for baking)

        """

        def render_func(request, *args, **kwargs):

            view = cls()

            context = view._get_view_context(request, *args, **kwargs)

            if isinstance(context, dict):
                context = view.extra_params(context)
                return view.context_to_html(request, context)
            else:
                # if we're returning a redirect view
                return context

        func = render_func
        func = handle_redirect(func)  # allow RedirectException
        if decorators:
            for v in cls.view_decorators:
                func = v(func)

        return func

    def access_denied_no_auth(self, request):
        """
        override to provide a better response if someone needs to login
        """
        return HttpResponse("No Access")

    def access_denied_no_staff(self, request):
        """
        override to provide a better response if someone needs to be staff
        """
        return HttpResponse("No Access")

    def _get_view_context(self, request, *args, **kwargs):
        context = self.view(request, *args, **kwargs)

        if isinstance(context, dict):
            context = self.extra_params(context)
        return context

    def extra_params(self, context):
        return context

    def context_to_html(self, request, context):
        html = render(request,
                      self.__class__.template,
                      context=context
                      )
        return html

    def view(self, request):
        return {}


class LogicalView(FunctionalView):
    """
    Runs with class-based logic while trying to keep the guts exposed. 

    request becomes self.request

    expects a 'logic' rather than a view function (no args).

    giving the class an 'args' list of strings tells it what to convert 
    view arguments into.

    e.g. args = ['id_no'] - will create self.id_no from the view argument. 
    if an arg is a tuple ('id_no','5') - will set a default value.

    Use prelogic and postlogic decorators to run functions before or afer logic.
    These accept an optional order paramter. 
    Lower order have priority.
    Default order is 5.

    """

    args = []

    def __init__(self):
        self.record_new = False
        self.values = []

    def __setattr__(self, key, value):
        if hasattr(self, "record_new") and self.record_new:
            self.values.append(key)
        super(FunctionalView, self).__setattr__(key, value)

    def view(self, request, *args, **kwargs):
        """
        override with something that returns a dictionary 
        to use plain functional view logic
        """
        self.request = request
        self.record_new = True  # enable new value recording

        arg_mappings = []
        """
        assign any default values
        """
        for a in self.__class__.args:
            if isinstance(a, tuple):
                setattr(self, a[0], a[1])
                arg_mappings.append(a[0])
            else:
                arg_mappings.append(a)
        """
        assign other results
        """
        for x, a in enumerate(args):
            try:
                arg_name = arg_mappings[x]
            except IndexError:
                raise ValueError("Mapping not assigned for {0}".format(a))
            setattr(self, arg_name, a)

        for k, v in kwargs.items():
            setattr(self, k, v)

        prelogic = self._prelogic()
        if prelogic:
            return prelogic
        logic = self.logic()
        if logic:
            return logic
        postlogic = self._postlogic()
        if postlogic:
            return postlogic

        return {k: getattr(self, k) for k in self.values}

    def _logic_processing(self, prefix):
        """
        run all pre and post logic functions in order.
        """
        def keying(v):
            if hasattr(v, "order"):
                return v.order
            else:
                return 5

        def ga(k):
            return getattr(self, k)
        """
        has a function had either a decorator or a name prefix assigned to it
        """
        def passes_func_test(k): return hasattr(
            k, "_prefix") and k._prefix == prefix

        def passes_test(k): return prefix + "_" in k or passes_func_test(ga(k))
        funcs = [k for k in dir(self) if passes_test(k)]
        funcs = [ga(k) for k in funcs]
        funcs.sort(key=lambda x: keying(x))
        for f in funcs:
            r = f()
            if r:  # if any value is returned, escalate
                return r

    def _prelogic(self):
        return self._logic_processing("prelogic")

    def _postlogic(self):
        return self._logic_processing("postlogic")

    def logic(self):
        """
        any new values assigned to self will be passed to the template
        self.value becomes value
        """
        pass


class prelogic(GenericDecorator):
    """
    decorates a function to run before the logic view
    accepts an order kwarg to manage competing functions
    """
    prefix = "prelogic"
    args_map = ["order"]
    default_kwargs = {"order": 5}

    def post_creation(self, obj):
        obj._prefix = self.__class__.prefix
        obj.order = self.order
        return obj


class postlogic(GenericDecorator):
    """
    decorates a function to run after the logic view
    accepts an order kwarg to manage competing functions
    """
    
    prefix = "postlogic"
    args_map = ["order"]
    default_kwargs = {"order": 5}

    def post_creation(self, obj):
        obj._prefix = self.__class__.prefix
        obj.order = self.order
        return obj
