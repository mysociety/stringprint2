"""Publication routes, ordered from specific resources to the article fallback."""

from django.urls import re_path
from . import views

PUBLICATION_VIEWS = (
    views.AssetView,
    views.HomeView,
    views.KindleView,
    views.EbookChapterView,
    views.TOCView,
    views.SearchView,
    views.SearchContentView,
    views.ParagraphMapView,
    views.TextView,
    views.KindleOPF,
    views.KindleNCX,
    views.RedirectLink,
    views.ArticleView,
)
urlpatterns = [
    re_path(pattern, view.as_view(), name=view.url_name)
    for view in PUBLICATION_VIEWS
    for pattern in view.url_patterns
]
# Longer static prefixes take precedence over the generic article pattern.
import re

urlpatterns.sort(
    key=lambda route: len(re.sub(r"\((.*?)\)", "1", str(route.pattern))), reverse=True
)
