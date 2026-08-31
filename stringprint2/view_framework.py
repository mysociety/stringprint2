"""
Small Django view primitives used by Stringprint's class-based views.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from importlib import import_module
from types import ModuleType
from typing import Any, Concatenate, ParamSpec, Protocol, TypeVar, cast

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Context, Template
from django.urls import URLPattern, re_path, reverse

Parameters = ParamSpec("Parameters")
ReturnValue = TypeVar("ReturnValue")
ViewMethod = Callable[Concatenate[Any, Parameters], ReturnValue]
ViewResult = dict[str, object] | HttpResponse | None


class RedirectException(Exception):
    """
    Request an HTTP redirect from view logic without returning early.
    """


class HookMethod(Protocol):
    """
    Carry lifecycle metadata attached by hook decorators.
    """

    view_hook: str
    order: int

    def __call__(self) -> ViewResult:
        """Run the lifecycle hook."""
        ...


def view_hook[**HookParameters, HookReturn](
    function: Callable[HookParameters, HookReturn],
    hook_name: str,
    order: int = 5,
) -> Callable[HookParameters, HookReturn]:
    """
    Attach lifecycle metadata to one view method.
    """
    hook = cast(HookMethod, function)
    hook.view_hook = hook_name
    hook.order = order
    return function


def before_logic[**HookParameters, HookReturn](
    function: Callable[HookParameters, HookReturn],
) -> Callable[HookParameters, HookReturn]:
    """
    Run a method before the main view logic.
    """
    return view_hook(function, "before")


def after_logic[**HookParameters, HookReturn](
    function: Callable[HookParameters, HookReturn],
) -> Callable[HookParameters, HookReturn]:
    """
    Run a method after the main view logic.
    """
    return view_hook(function, "after")


class StringprintView:
    """
    Render class-based Stringprint logic through Django.
    """

    template = ""
    args: tuple[str | tuple[str, object], ...] | list[str | tuple[str, object]] = ()
    view_decorators: tuple[Callable[..., object], ...] = ()
    url_pattern = ""
    url_patterns: tuple[str, ...] | list[str] = ()
    url_name = ""
    url_extra_args: dict[str, object] = {}

    share_image = ""
    share_site_name = ""
    share_image_alt = ""
    share_description = ""
    share_title = ""
    share_twitter = ""
    share_url = ""
    twitter_share_image = ""
    page_title = ""

    request: HttpRequest
    record_context: bool
    context_names: list[str]

    def __init__(self) -> None:
        object.__setattr__(self, "record_context", False)
        object.__setattr__(self, "context_names", [])

    def __setattr__(self, name: str, value: object) -> None:
        if self.record_context and name not in {"record_context", "context_names"}:
            self.context_names.append(name)
        object.__setattr__(self, name, value)

    @classmethod
    def as_view(cls, decorators: bool = True) -> Callable[..., HttpResponse]:
        """
        Return a Django view callable for this logic class.
        """

        def dispatch(
            request: HttpRequest, *args: object, **kwargs: object
        ) -> HttpResponse:
            view = cls()
            try:
                context = view.get_view_context(request, *args, **kwargs)
            except RedirectException as redirect:
                return HttpResponseRedirect(str(redirect))
            if isinstance(context, dict):
                return view.context_to_html(request, view.extra_params(context))
            return context

        wrapped: Callable[..., HttpResponse] = dispatch
        if decorators:
            for decorator in cls.view_decorators:
                wrapped = cast(Callable[..., HttpResponse], decorator(wrapped))
        return wrapped

    def get_view_context(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> dict[str, object] | HttpResponse:
        """
        Bind route arguments, run lifecycle hooks, and collect context values.
        """
        if type(self).view is not StringprintView.view:
            return self.view(request, *args, **kwargs)
        self.request = request
        self.record_context = True
        argument_names = []
        for argument in self.args:
            if isinstance(argument, tuple):
                name, default = argument
                setattr(self, name, default)
                argument_names.append(name)
            else:
                argument_names.append(argument)
        for index, value in enumerate(args):
            try:
                setattr(self, argument_names[index], value)
            except IndexError as error:
                raise ValueError(
                    f"No mapping assigned for argument {value!r}"
                ) from error
        for name, value in kwargs.items():
            setattr(self, name, value)

        result = self.run_hooks("before")
        if result is None:
            result = self.logic()
        if result is None:
            result = self.run_hooks("after")
        if result is not None:
            return result
        return {name: getattr(self, name) for name in self.context_names}

    def run_hooks(self, hook_name: str) -> ViewResult:
        """
        Run decorated lifecycle methods in declared order.
        """
        hooks = []
        for name in dir(self):
            method = getattr(self, name)
            if getattr(method, "view_hook", None) == hook_name:
                hooks.append(cast(HookMethod, method))
        hooks.sort(key=lambda method: int(getattr(method, "order", 5)))
        for method in hooks:
            result = method()
            if result is not None:
                return result
        return None

    def logic(self) -> ViewResult:
        """
        Implement view-specific logic.
        """
        return None

    def view(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> dict[str, object] | HttpResponse:
        """
        Implement direct request-based logic when lifecycle hooks are unused.
        """
        return {}

    def extra_params(self, context: dict[str, object]) -> dict[str, object]:
        """
        Add social metadata and the page title to a template context.
        """
        from django.conf import settings

        if hasattr(settings, "SITE_ROOT"):
            context["SITE_ROOT"] = settings.SITE_ROOT
        context["social_settings"] = self.social_settings(context)
        context["page_title"] = self.render_setting(self.page_title, context)
        return context

    def social_settings(self, context: dict[str, object]) -> dict[str, str]:
        """
        Render social metadata templates against a view context.
        """
        twitter_image = self.twitter_share_image or self.share_image
        return {
            "share_site_name": self.render_setting(self.share_site_name, context),
            "share_image": self.render_setting(self.share_image, context),
            "twitter_share_image": self.render_setting(twitter_image, context),
            "share_image_alt": self.render_setting(self.share_image_alt, context),
            "share_description": self.render_setting(self.share_description, context),
            "share_title": self.render_setting(self.share_title, context),
            "url": self.render_setting(self.share_url, context),
        }

    def render_setting(self, value: str, context: dict[str, object]) -> str:
        """
        Render one metadata template.
        """
        return Template(value).render(Context(context))

    def context_to_html(
        self, request: HttpRequest, context: dict[str, object]
    ) -> HttpResponse:
        """
        Render the configured Django template.
        """
        return render(request, self.template, context=context)

    @classmethod
    def redirect_response(cls, *args: object) -> HttpResponseRedirect:
        """
        Redirect to this view's named URL.
        """
        return HttpResponseRedirect(reverse(cls.url_name, args=args))

    @classmethod
    def get_patterns(cls) -> list[URLPattern]:
        """
        Build Django URL patterns declared by this view.
        """
        patterns = list(cls.url_patterns)
        if cls.url_pattern:
            patterns.append(cls.url_pattern)
        return [
            re_path(pattern, cls.as_view(), cls.url_extra_args, name=cls.url_name)
            for pattern in patterns
        ]


class DirectStringprintView(StringprintView):
    """
    Call ``view`` directly for request-oriented views.
    """

    def get_view_context(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> dict[str, object] | HttpResponse:
        """
        Delegate directly to the request-oriented view method.
        """
        return self.view(request, *args, **kwargs)


def patterns_for(module_or_name: str | ModuleType) -> list[URLPattern]:
    """
    Discover URL-enabled Stringprint view classes in one module.
    """
    module = (
        import_module(module_or_name)
        if isinstance(module_or_name, str)
        else module_or_name
    )
    view_classes = {
        value
        for value in module.__dict__.values()
        if isinstance(value, type)
        and issubclass(value, StringprintView)
        and value is not StringprintView
    }
    patterns = [pattern for view in view_classes for pattern in view.get_patterns()]
    patterns.sort(
        key=lambda pattern: len(re.sub(r"\((.*?)\)", "1", str(pattern.pattern))),
        reverse=True,
    )
    return patterns


def include_views(
    module_or_name: str | ModuleType,
) -> tuple[list[URLPattern], None, None]:
    """
    Return a Django include-compatible tuple for discovered views.
    """
    return patterns_for(module_or_name), None, None
