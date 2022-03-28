from django.conf.urls import url, include
from django.contrib import admin
from stringprint import views
from django.conf import settings
from django.conf.urls.static import static
from useful_inkleby.useful_django.views import AppUrl, include_view


urlpatterns = []

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += [
    url(r"^admin/", admin.site.urls),
    url(r"^preview/", include_view("stringprint.views")),
    url(r"^", include_view("frontend.views")),
]
