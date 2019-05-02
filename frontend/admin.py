from django.contrib import admin
from useful_inkleby.useful_django.admin import io_admin_register
# Register your models here.
from .models import UserSettings
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from useful_inkleby.useful_django.admin import io_admin_register
# Register your models here.


@io_admin_register(UserSettings)
class UserSettingsnAdmin(ImportExportModelAdmin):
    list_display = ('user', 'org')
