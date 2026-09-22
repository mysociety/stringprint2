from django.contrib import admin

from .models import Article, Organisation, HeaderImage, Version, Asset, OrgLinks

from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.models import User, Group
from django.db.models import Sum


class LinkInline(admin.TabularInline):
    model = OrgLinks


@admin.register(Article)
class ArticleAdmin(ImportExportModelAdmin):
    list_display = ("id", "title", "slug", "authors")
    search_fields = ("title",)
    actions = []


@admin.register(Organisation)
class OrganisationAdmin(ImportExportModelAdmin):
    list_display = ("id", "name", "twitter")
    search_fields = ("name",)
    inlines = (LinkInline,)


@admin.register(HeaderImage)
class HeaderImageAdmin(ImportExportModelAdmin):
    list_display = ("id", "article", "section_name", "image")
    search_fields = ("article",)


@admin.register(Version)
class VersionAdmin(ImportExportModelAdmin):
    list_display = ("id", "article", "label")
    search_fields = ("article",)


@admin.register(Asset)
class AssetAdmin(ImportExportModelAdmin):
    list_display = ("id", "article", "slug", "type")
    search_fields = ("slug",)
