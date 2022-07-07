from django.db import models

from useful_inkleby.useful_django.models import FlexiBulkModel
from django.contrib.auth.models import User
from stringprint.models import Organisation, Article
from django.utils.timezone import now
from django.core.files import File
import os
from django.conf import settings
from django.urls import reverse


class UserSettings(FlexiBulkModel):
    user = models.ForeignKey(User, related_name="settings", on_delete=models.CASCADE)
    org = models.ForeignKey(
        Organisation, related_name="user_settings", on_delete=models.CASCADE
    )
    tokens = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "User Settings"

    @classmethod
    def get_org(cls, user):
        if cls.objects.filter(user=user).exists() is False:
            default = Organisation.objects.all()[0]
            cls(user=user, org=default).save()
        return cls.objects.get(user=user).org

    @classmethod
    def change_org(cls, user, org):
        us = cls.get_settings(user)
        us.org = org
        us.save()

    @classmethod
    def get_settings(cls, user):
        return cls.objects.get(user=user)

    @classmethod
    def join(cls, user, org):
        us, created = cls.objects.get_or_create(user=user, org=org)
        return us


def org_download_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "org_{0}/download/{1}".format(instance.article.org_id, filename)


def get_file(fi):
    reopen = open(fi, "rb")
    django_file = File(reopen)
    return django_file
