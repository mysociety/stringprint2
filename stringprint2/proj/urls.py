from django.urls import include, path, re_path
from django.contrib import admin
from stringprint import views
from django.conf import settings
from django.conf.urls.static import static
from stringprint2.view_framework import include_views


urlpatterns = []

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r"^admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("manage/", include("publication_management.urls")),
    re_path(r"^preview/", include_views("stringprint.views")),
    re_path(r"^", include_views("frontend.views")),
]
