import re
import os

from django.shortcuts import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import mark_safe
from django.core.cache import cache
from stringprint2.charts import ChartCollection
from django.http import JsonResponse
from django.shortcuts import render
from django.template import Template, Context


from .models import Article, Asset
from django.views import View
from copy import copy
from stringprint2.services.render_context import PublicationRenderContext
from django.core.handlers.wsgi import WSGIRequest
from stringprint2.stringprint.models import Article, Version
from stringprint2.document_structure import Section
from stringprint2.services.paragraph_links import paragraph_compatibility_map
from typing import Any, Dict, List, Type, Union
from collections.abc import Callable


class PublicationView(View):
    """Normal Django dispatch with explicit context and a detached presentation snapshot."""

    template = ""
    publication = None
    redirect_target = None
    render_context = None
    search = False
    share_image = ""
    share_site_name = ""
    share_image_alt = ""
    share_description = ""
    share_title = ""
    share_twitter = ""
    share_url = ""
    twitter_share_image = ""
    page_title = ""

    @classmethod
    def as_view(
        cls, decorators: bool = True, **kwargs: Any
    ) -> Callable[..., HttpResponse]:
        return super().as_view(**kwargs)

    def get(self, request, *args, **kwargs):
        result = self.view(request, *args, **kwargs)
        if isinstance(result, dict):
            return self.context_to_html(request, self.extra_params(result))
        return result

    def get_article(self, request, article_slug):
        persisted = (
            self.publication
            if self.publication is not None
            else Article.objects.get(slug=article_slug)
        )
        # Legacy templates still call Article helpers. Their transient attributes
        # belong exclusively to this page's snapshot, never the persisted instance.
        article = copy(persisted)
        options = self.render_context or PublicationRenderContext()
        article.baking = options.baking
        article.search = self.search
        article.paywall = False
        return article

    def extra_params(self, context):
        context.setdefault("SITE_ROOT", settings.SITE_ROOT)
        context.update(
            (self.render_context or PublicationRenderContext()).template_values()
        )
        context["social_settings"] = self.social_settings(context)
        context["page_title"] = self.render_setting(self.page_title, context)
        return context

    def render_setting(self, value, context):
        return Template(value).render(Context(context))

    def social_settings(self, context):
        return {
            key: self.render_setting(value, context)
            for key, value in {
                "share_site_name": self.share_site_name,
                "share_image": self.share_image,
                "twitter_share_image": self.twitter_share_image or self.share_image,
                "share_image_alt": self.share_image_alt,
                "share_description": self.share_description,
                "share_title": self.share_title,
                "url": self.share_url,
            }.items()
        }

    def context_to_html(self, request, context):
        return render(request, self.template, context=context)


class AssetView(PublicationView):
    template = "ink//asset.html"
    url_patterns = [r"^asset/(.*)/(.*)/(.*)/", r"^asset/(.*)/(.*)/"]
    url_name = "asset_view"

    def view(self, request, article_slug, slug, static=None):
        from stringprint2.charts import ChartCollection, Chart

        a = Asset.objects.get(article__slug=article_slug, slug=slug)

        if a.chart:
            charts = [a.chart]
        else:
            charts = []

        c = ChartCollection(charts)
        if static:
            c.make_static = True

        return {"asset": a, "chart_collection": c}


class HomeView(PublicationView):
    share_image = settings.SHARE_IMAGE
    twitter_share_image = settings.TWITTER_SHARE_IMAGE
    share_description = settings.SITE_DESCRIPTION
    share_site_name = settings.SITE_NAME
    share_title = settings.SITE_NAME
    page_title = settings.SITE_NAME
    share_twitter = settings.SITE_TWITTER
    template = "ink//home.html"
    url_patterns = [r"^$"]
    url_name = "home_view"

    def view(self, request):
        return {
            "books": Article.objects.all().order_by("-publish_date"),
        }


class KindleView(HomeView):
    """
    view to create the kindle version of an article
    """

    template = "ink//kindle.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/kindle"]
    url_name = "kindle_view"
    require_staff = False
    txt_mode = "kindle"

    def restrict(self, sections: List[Section], code: str) -> List[Section]:
        if code:
            return [x for x in sections if x.anchor() == code]
        else:
            return sections

    def view(
        self, request: WSGIRequest, article_slug: str, paragraph_code: str = ""
    ) -> dict:
        a = self.get_article(request, article_slug)
        c = a.display_content()
        c.sections = self.restrict(c.sections, paragraph_code)
        for s in c.sections:
            s._article = a
        a.cached_assets = [x for x in a.assets.all()]
        return {
            "article": a,
            "content": c,
            "txt_mode": self.__class__.txt_mode,
            "debug": settings.DEBUG,
        }


class EbookChapterView(KindleView):
    """
    Render ebook chapter
    """

    template = "ink//epub_chapter.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/epub/([A-Za-z0-9_-]+)/"]
    url_name = "epub_view"


class TOCView(HomeView):
    """
    view to create json toc
    """

    url_patterns = [r"^([A-Za-z0-9_-]+)/tocjson"]
    url_name = "json_toc_view"
    require_staff = True

    def view(self, request, article_slug, paragraph_code=""):
        a = self.get_article(request, article_slug)

        c = a.display_content()

        response = []

        def fix_trailing_numbers(v):
            r = re.search(r"\d+\.\d*(.+)", v)
            if r:
                return r.groups()[0].strip()
            else:
                return v

        social_url = a.social_url()

        def get_item_and_children(i):
            item = {
                "name": fix_trailing_numbers(i.name),
                "link": social_url + i.nav_url,
            }
            item["children"] = [get_item_and_children(x) for x in i.children()]
            return item

        toc = c.toc()
        response = [get_item_and_children(x) for x in toc.level_1()]

        return JsonResponse(response, safe=False)


class SearchView(HomeView):
    search = True

    """
    Render the publication search page.
    """

    template = "ink//search.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/search"]
    url_name = "publication_search"

    def view(self, request, article_slug, paragraph_code=""):
        a = self.get_article(request, article_slug)
        c = a.display_content()

        for s in c.sections:
            if s.grafs:
                a.nav_default_range = list(range(s.order, s.order + 3))
                break

        return {"article": a, "content": c, "cache_nav": "full"}


class SearchContentView(SearchView):
    """
    Render the JavaScript publication search index.
    """

    template = "ink//search_js.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/search_content.js"]
    url_name = "publication_search_content"

    def context_to_html(
        self, request: WSGIRequest, context: dict[str, object]
    ) -> HttpResponse:
        """
        Render the search index with an executable JavaScript MIME type.
        """
        return render(
            request,
            self.template,
            context=context,
            content_type="application/javascript",
        )


class ParagraphMapView(SearchView):
    """
    Serve legacy paragraph mappings only when a client requests them.
    """

    url_patterns = [r"^([A-Za-z0-9_-]+)/paragraph_map.json"]
    url_name = "paragraph_map"

    def context_to_html(
        self, request: WSGIRequest, context: dict[str, object]
    ) -> JsonResponse:
        content = context["content"]
        return JsonResponse(
            paragraph_compatibility_map(content.paragraph_lookup()),
            json_dumps_params={"separators": (",", ":")},
        )


class TextView(KindleView):
    """
    view to create the plain text version
    """

    template = "ink//plain.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/text/"]
    url_name = "txt_view"
    require_staff = True
    txt_mode = "text"


class KindleOPF(KindleView):
    """
    view to create the kindle version of an article
    """

    template = "ink//kindle.opf"
    url_patterns = [r"^(.*)/kindle/opf"]
    url_name = "kindle_opf"


class KindleNCX(KindleView):
    """
    view to create the kindle version of an article
    """

    template = "ink//toc.ncx"
    url_patterns = [r"^(.*)/kindle/ncx"]
    url_name = "kindle_ncx"


class ArticleView(HomeView):
    """
    view to create the live version of a page
    """

    template = "ink//article_main.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/", r"^([A-Za-z0-9_-]+)/(.*)"]
    url_name = "article_view"
    share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    twitter_share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    share_description = "{% if article.multipage %}Chapter {{article.active_section.order}}. {{article.active_section.name}}{%else%}{{article.description}}{% endif %}"
    share_title = "{{article.title}}"
    share_twitter = "{{article.org.twitter}}"
    share_site_name = "{{article.org.name}}"
    page_title = "{{article.title}}"
    share_url = "{{article.social_url}}"

    def extra_params(self, context):
        params = super(ArticleView, self).extra_params(context)
        extra = {
            "social_settings": self.social_settings(params),
            "page_title": self._page_title(params),
        }
        params.update(extra)
        return params

    def _page_title(self, context):
        c_context = Context(context)
        return Template(self.__class__.page_title).render(c_context)

    def social_settings(self, context):
        """
        run class social settings against template
        """
        cls = self.__class__

        c_context = Context(context)

        def process(x):
            return Template(x).render(c_context)

        if cls.twitter_share_image:
            twitter_img = cls.twitter_share_image
        else:
            twitter_img = cls.share_image

        di = {
            "share_site_name": process(cls.share_site_name),
            "share_image": process(cls.share_image),
            "twitter_share_image": process(twitter_img),
            "share_image_alt": process(cls.share_image_alt),
            "share_description": process(cls.share_description),
            "share_title": process(cls.share_title),
            "url": process(cls.share_url),
            "share_image_alt": process(cls.share_image_alt),
        }

        return di

    def view(self, request, article_slug, section_slug=""):
        a = self.get_article(request, article_slug)
        self.article = a
        """
        lets the bake view interact with the settings for the article
        """

        """
        move these along if we're not loading over multiple pages
        """
        if a.multipage is False:
            paragraph_code = section_slug
            section_slug = ""

        """
        how much of the page do we have access to?
        """
        if "screenshot" in request.GET:
            a.making_screenshot = True
            a.multipage = False

        display_first_section = False
        if a.multipage:
            if section_slug == "":
                display_first_section = True
                slugs = []
            else:
                slugs = [section_slug]
        else:
            slugs = []

        """
        limit if all in one page
        """

        para = "full"
        c = a.display_content(slugs, display_first_section)
        message = ""

        for s in c.sections:
            if s.grafs and s.active_section:
                a.nav_default_range = list(range(s.order, s.order + 3))
                a.active_section = s
                break

        """
        prepare assets for charts and images
        """
        titles_and_images = list(a.headers_and_images())
        if a.multipage and hasattr(a, "active_section"):
            asset_ids = a.active_section.used_assets()
        else:
            asset_ids = c.used_assets()
        a.cached_titles_and_images = [
            x for x in titles_and_images if x.is_title or x.id in asset_ids
        ]
        a.cached_assets = [x for x in a.assets.filter(active=True) if x.id in asset_ids]
        chart_assets = [x.chart for x in a.cached_assets if x.chart]
        chart_collection = ChartCollection(chart_assets)

        a.prep_image_lookup()
        return {
            "article": a,
            "content": c,
            "debug": settings.DEBUG,
            "message": message,
            "first_multi_page": display_first_section,
            "section_slug": section_slug,
            "chart_collection": chart_collection,
        }

    def _get_template_path(self):
        """
        override with the specific org template
        if available
        """
        template_path = self.__class__.template
        org = self.article.org
        template_dir = org.template_dir
        if template_dir:
            possible_path = os.path.join(template_dir, template_path)
            if os.path.exists(possible_path):
                return org.slug + "/templates/" + template_path
        return template_path

    def context_to_html(self, request, context):
        html = render(request, self._get_template_path(), context=context)
        return html


class RedirectLink(HomeView):
    """
    view to create the live version of a page
    """

    template = "ink//redirect.html"
    url_patterns = [r"^([A-Za-z0-9_-]+)/l/(.*)"]
    url_name = "redirect_link"
    share_site_name = "{{article.org.name}}"
    share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    twitter_share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    share_twitter = "{{article.org.twitter}}"

    def load_article(self, request, article_slug, paragraph_code):
        self.article = self.get_article(request, article_slug)
        if self.redirect_target is not None:
            self.content, self.graf, self.paragraph_tag = self.redirect_target
            if self.graf:
                self.graf._article = self.article
            return
        self.content = self.article.display_content()
        graf, section = self.content.get_paragraph(paragraph_code)
        if graf:
            graf._section = section
            graf._article = self.article
        self.paragraph_tag = None
        self.graf = graf

    def view(self, request, article_slug, paragraph_code):
        self.load_article(request, article_slug, paragraph_code)
        self.asset_image = None
        self.alt = ""
        if self.graf:
            self.alt = self.graf.display_bare()
            if self.graf.asset:
                asset = Asset.objects.get(id=self.graf.asset)
                if asset.image:
                    self.asset = asset
                    self.asset_image = self.asset.get_share_image()
                    asset_caption = self.asset.search_name()
                    if asset_caption:
                        self.alt = asset_caption

        return {
            "article": self.article,
            "content": self.content,
            "graf": self.graf,
            "alt": self.alt,
            "asset_image": self.asset_image,
            "paragraph_tag": self.paragraph_tag,
        }
