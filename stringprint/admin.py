from django.contrib import admin
from useful_inkleby.useful_django.admin import io_admin_register
# Register your models here.
from .models import Article, Organisation, HeaderImage, Version, Asset, MultiSection, OrgLinks

from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.models import User, Group
from django.db.models import Sum


class LinkInline(admin.TabularInline):
    model = OrgLinks


@io_admin_register(Article)
class ArticleAdmin(ImportExportModelAdmin):
    list_display = ('id', 'title', 'slug', 'authors')
    search_fields = ('title',)
    actions = []


@io_admin_register(Organisation)
class OrganisationAdmin(ImportExportModelAdmin):
    list_display = ('id', 'name', 'twitter')
    search_fields = ('name',)
    inlines = (LinkInline,)


@io_admin_register(HeaderImage)
class HeaderImageAdmin(ImportExportModelAdmin):
    list_display = ('id', 'article', 'section_name', 'image')
    search_fields = ('article',)


@io_admin_register(Version)
class VersionAdmin(ImportExportModelAdmin):
    list_display = ('id', 'article', 'label')
    search_fields = ('article',)


@io_admin_register(Asset)
class AssetAdmin(ImportExportModelAdmin):
    list_display = ('id', 'article', 'slug', 'type')
    search_fields = ('slug',)


@io_admin_register(MultiSection)
class MultiSectionAdmin(ImportExportModelAdmin):
    list_display = ('version', 'anchor', 'order')
