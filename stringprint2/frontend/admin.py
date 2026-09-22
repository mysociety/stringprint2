from django.contrib import admin

from .models import UserSettings
from import_export.admin import ImportExportModelAdmin


@admin.register(UserSettings)
class UserSettingsnAdmin(ImportExportModelAdmin):
    list_display = ("user", "org")
