"""Explicit routes for account pages and historical management links."""

from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.CatalogRedirectView.as_view(), name="home"),
    path("register/", views.RegisterView.as_view(), name="register"),
    re_path(
        r"^document/(?P<article_id>[0-9]+)/headers",
        views.ArticleHeadersView.as_view(),
        name="article.headers",
    ),
    re_path(
        r"^document/(?P<article_id>[0-9]+)/settings/",
        views.ArticleSettingsView.as_view(),
        name="article.settings",
    ),
    re_path(
        r"^document/(?P<article_id>[0-9]+)/publish",
        views.PublicationRedirectView.as_view(),
        name="article.publish",
    ),
    re_path(
        r"^document/(?P<article_id>[0-9]+)/reupload",
        views.PublicationRedirectView.as_view(),
        name="document.reupload",
    ),
    re_path(r"^document/new", views.CatalogRedirectView.as_view(), name="document.new"),
    re_path(
        r"^documents/list/(?P<page_no>.*)",
        views.CatalogRedirectView.as_view(),
        name="document.list",
    ),
    re_path(
        r"^documents/list", views.CatalogRedirectView.as_view(), name="document.list"
    ),
    re_path(r"^org/settings", views.OrgSettingsView.as_view(), name="org.settings"),
    re_path(
        r"^orgs/change/(?P<org_id>[0-9]+)",
        views.ChangeOrgView.as_view(),
        name="org.change",
    ),
]
