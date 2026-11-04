from django.urls import include, path, re_path
from django.contrib import admin
from stringprint2.stringprint import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = []

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    re_path(r"^admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("manage/", include("stringprint2.publication_management.urls")),
    re_path(r"^preview/", include("stringprint2.stringprint.urls")),
    re_path(r"^", include("stringprint2.frontend.urls")),
]
