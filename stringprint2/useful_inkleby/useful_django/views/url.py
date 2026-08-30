'''

IntegratedURLView - Sidestep django's url.py based setup and integrate
urls directly with view classes rather than keeping them seperate.

This will mix-in either with the functional inkleby view or the default
django class-based views. 

In views module you set up a series of classes that inherit from
IntegratedURLView and then connect up in project url like so:

url(r'^foo/', include_view('foo.views')),

Philosophy behind this is that the current urlconf system was designed for
functional views - class-based  views have to hide themselves as functions 
with an as_view function, which is ugly. By moving responsibility for 
generating these to the class view it avoids awkward manual repetition 
and keeps all settings associated with the view in one place.
Apps then don't need a separate url.py. 

'''

import re
import six
from importlib import import_module
from types import ModuleType

from django.urls import (
    LocalePrefixPattern, reverse, re_path as url
)
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import HttpResponseRedirect


from .functional import FunctionalView, LogicalView



def make_comparison(v):
    text = v
    for s in re.findall("\((.*?)\)", v):
        text = text.replace(s, "1")
    return text


class AppUrl(object):

    def __init__(self, app_view):
        """

        Given path to views (or views module) will gather all url-enabled views
        """
        self.views = []

        if isinstance(app_view, ModuleType):
            view_module = app_view
        elif isinstance(app_view, six.string_types):
            view_module = import_module(app_view)
        else:
            raise TypeError("Not a module or module path")

        for k, v in view_module.__dict__.items():
            if isinstance(v, type) and issubclass(v, IntegratedURLView):
                self.views.append(v)

    def patterns(self):
        """
        return patterns of all associated views
        """

        local_patterns = []
        for c in self.views:
            local_patterns.extend(c.get_pattern())

        local_patterns.sort(key=lambda x: len(x._url_comparison), reverse=True)
        return local_patterns

    def has_bakeable_views(self):
        for v in self.views:
            if hasattr(v, "bake_args") and hasattr(v,"url_name"):
                if v.url_name:
                    return True
        return False

    def bake(self, **kwargs):
        """
        bake all views with a bake_path
        """
        for v in self.views:
            if hasattr(v, "bake_args") and hasattr(v,"url_name"):
                if v.url_name:
                    v.bake(**kwargs)


def include_view(arg, namespace=None, app_name=None):
    if app_name and not namespace:
        raise ValueError('Must specify a namespace if specifying app_name.')

    if isinstance(arg, tuple):
        # callable returning a namespace hint
        if namespace:
            raise ImproperlyConfigured(
                'Cannot override the namespace for a dynamic module that provides a namespace')
        urlconf_module, app_name, namespace = arg
    else:
        # No namespace hint - use manually provided namespace
        urlconf_module = arg

    if isinstance(urlconf_module, six.string_types):
        urlconf_module = import_module(urlconf_module)

    patterns = AppUrl(urlconf_module).patterns()
    urlconf_module.urlpatterns = patterns

    patterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)

    # Make sure we can iterate through the patterns (without this, some
    # testcases will break).
    if isinstance(patterns, (list, tuple)):
        for url_pattern in patterns:
            # Test if the LocaleRegexURLResolver is used within the include;
            # this should throw an error since this is not allowed!
            if isinstance(url_pattern, LocalePrefixPattern):
                raise ImproperlyConfigured(
                    'Using i18n_patterns in an included URLconf is not allowed.')

    return (urlconf_module, app_name, namespace)

    return


class IntegratedURLView(LogicalView):
    """

    Integrate URL configuration information into the View class.

    Makes app level urls.py unnecessary. 

    add class level variables for:

    url_pattern - regex string
    url_patterns - list of regex strings (optional)
    url_name - name for url view (for reverse lookup)
    url_extra_args - any extra arguments to be fed into the url function for this view.

    """

    url_pattern = ""
    url_patterns = []
    url_name = ""
    url_extra_args = {}

    @classmethod
    def redirect_response(cls, *args):
        return HttpResponseRedirect(reverse(cls.url_name, args=args))

    @classmethod
    def get_pattern(cls):
        """
        returns a list of conf.url objects for url patterns that match this object
        """
        new_patterns = []

        def urlformat(pattern):
            uo = url(pattern, cls.as_view(),
                     cls.url_extra_args, name=cls.url_name)
            uo._url_comparison = make_comparison(pattern)
            return uo
        if cls.url_patterns:
            new_patterns = [urlformat(x) for x in cls.url_patterns]
        if cls.url_pattern:
            new_patterns.append(urlformat(cls.url_pattern))

        return new_patterns
