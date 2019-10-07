from django.shortcuts import HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.html import mark_safe
from django.core.cache import cache
from charts import ChartCollection
from useful_inkleby.useful_django.views.functional import postlogic
from django.http import JsonResponse
from django.shortcuts import render
from django.template import Template, Context
from django.dispatch import receiver
from compressor.signals import post_compress
import re

from .models import Article
from useful_inkleby.useful_django.views import ComboView


@receiver(post_compress)
def compression_callback(sender, type, mode, context, **kwargs):
    """
    Logs files compressed back into the article object
    this lets the rendering process capture and move them
    """
    article = context["article"]
    if hasattr(article, "compressed_files") is False:
        article.compressed_files = []
    article.compressed_files.append(context["compressed"]["url"])


class AssetView(ComboView):

    template = "ink//asset.html"
    url_patterns = [r'^asset/(.*)/(.*)/(.*)/', r'^asset/(.*)/(.*)/']
    url_name = "asset_view"

    def view(self, request, article_slug, slug, static=None):

        from charts import ChartCollection, GoogleChart

        a = Asset.objects.get(article__slug=article_slug, slug=slug)

        if a.chart:
            charts = [a.chart]
        else:
            charts = [charts]

        c = ChartCollection(charts)
        if static:
            c.make_static = True

        return {'asset': a, 'chart_collection': c}


class HomeView(ComboView):
    share_image = settings.SHARE_IMAGE
    twitter_share_image = settings.TWITTER_SHARE_IMAGE
    share_description = settings.SITE_DESCRIPTION
    share_site_name = settings.SITE_NAME
    share_title = settings.SITE_NAME
    page_title = settings.SITE_NAME
    share_twitter = settings.SITE_TWITTER
    template = "ink//home.html"
    url_patterns = [r'^$']
    url_name = "home_view"

    def view(self, request):

        return {'books': Article.objects.filter(public=True), }


class KindleView(HomeView):
    """
    view to create the kindle version of an article
    """
    template = "ink//kindle.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/kindle']
    url_name = "kindle_view"
    require_staff = False
    txt_mode = "kindle"
    article_settings_override = {"baking": False, "search": False}

    def get_article(self, request, article_slug):
        a = Article.objects.get(slug=article_slug)
        """
        lets the bake view interact with the settings for the article
        """
        if self.__class__.article_settings_override:
            a.__dict__.update(self.__class__.article_settings_override)
        return a

    def view(self, request, article_slug, paragraph_code=""):

        a = self.get_article(request, article_slug)
        c = a.display_content()

        for s in c.sections:
            s._article = a
        a.cached_assets = [x for x in a.assets.all()]
        return {"article": a,
                'content': c,
                'txt_mode': self.__class__.txt_mode,
                'debug': settings.DEBUG}


class TOCView(HomeView):
    """
    view to create json toc
    """
    url_patterns = [r'^([A-Za-z0-9_-]+)/tocjson']
    url_name = "json_toc_view"
    require_staff = True
    article_settings_override = {"search": False}

    def get_article(self, request, article_slug):
        return Article.objects.get(slug=article_slug)

    def view(self, request, article_slug, paragraph_code=""):

        a = self.get_article(request, article_slug)

        if self.__class__.article_settings_override:
            a.__dict__.update(self.__class__.article_settings_override)

        c = a.display_content()

        response = []

        def fix_trailing_numbers(v):
            r = re.search("\d+\.\d*(.+)", v)
            if r:
                return r.groups()[0].strip()
            else:
                return v

        social_url = a.social_url()

        def get_item_and_children(i):
            item = {"name": fix_trailing_numbers(i.name),
                    "link": social_url + i.nav_url}
            item["children"] = [get_item_and_children(x) for x in i.children()]
            return item

        toc = c.toc()
        response = [get_item_and_children(x) for x in toc.level_1()]

        return JsonResponse(response, safe=False)


class TipueSearchView(HomeView):
    """
    view to create the search page for tipue
    """
    template = "ink//search.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/search']
    url_name = "tipue_search"
    article_settings_override = {"baking": False,
                                 "search": True}

    def get_article(self, request, article_slug):
        return Article.objects.get(slug=article_slug)

    def view(self, request, article_slug, paragraph_code=""):

        a = self.get_article(request, article_slug)
        if self.__class__.article_settings_override:
            a.__dict__.update(self.__class__.article_settings_override)
        c = a.display_content()
        
        for s in c.sections:
            if s.grafs:
                a.nav_default_range = list(range(s.order, s.order + 3))
                break

        return {"article": a,
                'content': c,
                'cache_nav': 'full'}


class TipueContentView(TipueSearchView):
    """
    view to create the contentfile for searches
    """
    template = "ink//search_js.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/tipuesearch_content.js']
    url_name = "tipue_content"


class TextView(KindleView):
    """
    view to create the plain text version
    """
    template = "ink//plain.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/text/']
    url_name = "txt_view"
    require_staff = True
    txt_mode = "text"


class KindleOPF(KindleView):
    """
    view to create the kindle version of an article
    """
    template = "ink//kindle.opf"
    url_patterns = [r'^(.*)/kindle/opf']
    url_name = "kindle_opf"


class KindleNCX(KindleView):
    """
    view to create the kindle version of an article
    """
    template = "ink//toc.ncx"
    url_patterns = [r'^(.*)/kindle/ncx']
    url_name = "kindle_ncx"


class ArticleView(HomeView):
    """
    view to create the live version of a page
    """
    template = "ink//article_main.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/',
                    r'^([A-Za-z0-9_-]+)/(.*)']
    url_name = "article_view"
    share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    twitter_share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    share_description = "{{article.description}}"
    share_title = "{{article.title}}"
    share_twitter = "{{article.org.twitter}}"
    share_site_name = "{{article.org.name}}"
    page_title = "{{article.title}}"
    share_url = "{{article.social_url}}"
    article_settings_override = {"baking": False, "search": False}

    def extra_params(self, context):
        params = super(ArticleView, self).extra_params(context)
        if hasattr(settings, "SITE_ROOT"):
            params["SITE_ROOT"] = settings.SITE_ROOT
        extra = {"social_settings": self.social_settings(params),
                 "page_title": self._page_title(params)}
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

        def process(x): return Template(x).render(c_context)

        if cls.twitter_share_image:
            twitter_img = cls.twitter_share_image
        else:
            twitter_img = cls.share_image

        di = {'share_site_name': process(cls.share_site_name),
              'share_image': process(cls.share_image),
              'twitter_share_image': process(twitter_img),
              'share_image_alt': process(cls.share_image_alt),
              'share_description': process(cls.share_description),
              'share_title': process(cls.share_title),
              'url': process(cls.share_url),
              'share_image_alt': process(cls.share_image_alt),
              }

        return di

    def context_to_html(self, request, context):
        html = render(request,
                      self.__class__.template,
                      context=context
                      )
        return html

    def get_article(self, request, article_slug):
        return Article.objects.get(slug=article_slug)

    def view(self, request, article_slug, section_slug=""):
        a = self.get_article(request, article_slug)
        """
        lets the bake view interact with the settings for the article
        """
        if self.__class__.article_settings_override:
            a.__dict__.update(self.__class__.article_settings_override)

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

        if a.multipage:
            if section_slug == "":
                section_slug = a.first_section_name
                slugs = [section_slug]
            else:
                slugs = [section_slug]
        else:
            slugs = []

        """
        limit if all in one page
        """

        para = "full"
        c = a.display_content(slugs)
        message = ""
        
        for s in c.sections:
            if s.grafs and s.active_section:
                a.nav_default_range = list(range(s.order, s.order + 3))
                break

        """
        prepare assets for charts
        """
        asset_slugs = c.used_assets()
        a.cached_assets = [x for x in a.assets.filter(
            active=True) if x.id in asset_slugs]
        chart_assets = [x.chart for x in a.cached_assets if x.chart]
        chart_collection = ChartCollection(chart_assets)

        a.prep_image_lookup()
        return {"article": a,
                'content': c,
                'debug': settings.DEBUG,
                'message': message,
                'chart_collection': chart_collection}


class RedirectLink(HomeView):
    """
    view to create the live version of a page
    """
    template = "ink//redirect.html"
    url_patterns = [r'^([A-Za-z0-9_-]+)/l/(.*)']
    url_name = "redirect_link"
    share_site_name = "{{article.org.name}}"
    share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    twitter_share_image = "{{SITE_ROOT}}{{article.get_share_image}}"
    share_twitter = "{{article.org.twitter}}"

    article_settings_override = {"baking": False, "search": False}

    def load_article(self, request, article_slug, paragraph_code):
        self.article = Article.objects.get(slug=article_slug)
        if self.__class__.article_settings_override:
            self.article.__dict__.update(
                self.__class__.article_settings_override)
        self.content = self.article.display_content()
        graf, section = self.content.get_paragraph(paragraph_code)
        graf._section = section
        graf._article = self.article
        self.paragraph_tag = None
        self.graf = graf

    def view(self, request, article_slug, paragraph_code):

        self.load_article(request, article_slug, paragraph_code)

        return {"article": self.article,
                'content': self.content,
                'graf': self.graf,
                'paragraph_tag':self.paragraph_tag}
