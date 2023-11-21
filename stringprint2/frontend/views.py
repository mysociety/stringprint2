from useful_inkleby.useful_django.views import (
    ComboView,
    RedirectException,
    prelogic,
    postlogic,
)
from . import forms as ff
import os
from stringprint.models import Article, Organisation
from django.utils.text import slugify
from .models import UserSettings
from django.contrib.auth import authenticate, login
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.timezone import now
from markdown import markdown
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
import html2text
from wsgiref.util import FileWrapper
from django.shortcuts import HttpResponse
from django.conf import settings


class GroupedPage(Page):
    def grouped_release(self):
        """
        release in groups of two
        """
        release = []
        for i in self:
            release.append(i)
            if len(release) == 2:
                yield release
                release = []
        if release:
            yield release

    def reasonable_range(self):
        """
        return a 'nice' range that gives
        5 either side + links to first and last
        """

        max_pages = self.paginator.num_pages
        number = self.number
        full_range = 10
        h_range = full_range / 2
        lower = number - h_range
        higher = number + h_range
        start = []
        end = []

        if max_pages < full_range:
            return list(range(1, max_pages + 1))

        if lower < 1:
            lower = 1
        elif lower > 1:
            lower += 1
            start = [1]
        if higher > max_pages:
            higher = max_pages
        elif higher < max_pages:
            higher -= 1
            end = [max_pages]

        return start + list(range(lower, higher)) + end


def get_admin_user():
    if User.objects.filter(username="admin").exists() is False:
        User.objects.create_superuser(
            "admin", password="admin", email="local@127.0.0.1"
        )
    return User.objects.get(username="admin")


class GroupedPaginator(Paginator):
    def _get_page(self, *args, **kwargs):
        return GroupedPage(*args, **kwargs)


class LoggedInView(ComboView):
    require_login = False

    @prelogic
    def generic(self):
        self.url_name = self.__class__.url_name

    @prelogic
    def get_org(self):
        if self.request.user.is_authenticated is False:
            admin_user = get_admin_user()
            login(self.request, admin_user)
        self.org = UserSettings.get_org(self.request.user)

    def access_denied_no_auth(self, request):
        raise RedirectException(reverse("login"))


class ArticleEditBase(ComboView):
    """
    article based editing views
    """

    args = ["article_id"]

    @prelogic
    def get_article(self):
        org = UserSettings.get_org(self.request.user)
        try:
            self.article = Article.objects.get(id=self.article_id, org=org)
        except Article.DoesNotExist:
            raise RedirectException(reverse("home"))

        if self.article.reprocessing():
            self.message = "This document is currently being processed. \
                            You will be able to see changes in a few minutes."
            self.refresh = True


class ArticleHeadersView(ArticleEditBase, LoggedInView):
    template = "frontend//doc_headers.html"
    url_patterns = [r"^document/(.*)/headers"]
    url_name = "article.headers"

    def logic(self):
        header = self.article.images.filter(title_image=True)
        if header.exists():
            instance = header[0]
        else:
            instance = None

        if self.request.POST:
            print(self.request.FILES)
            form = ff.PageHeaderImageForm(self.request.POST, instance=instance)
            if form.is_valid():
                self.message = "Header Updated"
                form.save(self.article, files=self.request.FILES)
        else:
            form = ff.PageHeaderImageForm(instance=instance)

        self.form = form
        self.submit_text = "Change Title Image"


class ArticleEditView(ArticleEditBase, LoggedInView):
    template = "frontend//doc_edit.html"
    url_patterns = [r"^document/(.*)/edit"]
    url_name = "article.edit"

    def logic(self):
        """
        edit the text of the document
        """
        if self.request.POST:
            new_text = self.request.POST["new_text"]
            html_2_markdown = html2text.HTML2Text()
            new_text = html_2_markdown.handle(new_text)
            c = self.article.content()
            c.raw = new_text
            c.save()
            self.article.trigger_reprocess()

        raw = self.article.content().raw
        if raw:
            self.raw = mark_safe(markdown(raw))
        else:
            self.raw = ""


class ArticlePublishView(ArticleEditBase, LoggedInView):
    template = "frontend//doc_publish.html"
    url_patterns = [r"^document/(.*)/publish"]
    url_name = "article.publish"
    form = ff.ArticlePublishForm

    def logic(self):
        """
        configure the publishing screen
        """

        self.settings = UserSettings.get_settings(self.request.user)

        default_url = "http://research.blah.com/{0}".format(self.article.slug)
        default_date = self.article.publish_date
        if default_date == None:
            default_date = now().date

        if self.request.POST:
            form = self.form(self.request.POST, setting_url=default_url)
            if form.is_valid():
                self.article.production_url = form.cleaned_data["publish_url"]
                self.article.publish_date = form.cleaned_data["publish_date"]
                self.article.save()

                if self.article.publish_tokens != -999:
                    if self.article.publish_tokens <= 0:
                        if self.settings.tokens > 0 or self.settings.tokens == -999:
                            self.article.publish_tokens += 11
                            self.article.save()
                            if self.settings.tokens != -999:
                                self.settings.tokens -= 1
                                self.settings.save()

                if self.article.publish_tokens:
                    self.article.trigger_render()
                else:
                    self.message = "danger|You need more tokens."

        else:
            form = self.form(
                initial={
                    "publish_url": self.article.production_url,
                    "publish_date": default_date,
                },
                setting_url=default_url,
            )

        self.form = form
        self.submit_text = "Publish"

        if self.settings.tokens == 0 and self.article.publish_tokens == 0:
            url = reverse("tokens")
            url = '<a href="{0}">{1}</a>'.format(url, "Click here to get tokens.")
            self.message = "danger|You need more tokens to render this document. " + url

        """
        what is currently happening?
        """
        self.downloads = self.article.downloads.all().order_by(
            "-time_requested", "-time_completed"
        )
        if self.downloads.exists() and self.downloads[0].time_completed == None:
            self.refresh = True
            self.message = "Your document is currently rendering. This page will refresh when it is finished."
        elif self.downloads.exists():
            self.last_download = self.downloads[0]


class ArticleSettingsView(ArticleEditBase, LoggedInView):
    template = "frontend//document_settings.html"
    url_patterns = [r"^document/([0-9]*)/settings/"]
    url_name = "article.settings"
    form = ff.ArticleEditForm

    def logic(self):
        if self.request.POST:
            form = self.form(self.request.POST, instance=self.article)
            if form.is_valid():
                form.save()
                self.message = "Settings Updated"
        else:
            form = self.form(instance=self.article)

        self.form = form
        self.submit_text = "Submit Changes"


class OrgSettingsView(LoggedInView):
    template = "frontend//org_amend.html"
    url_patterns = [r"^org/settings"]
    url_name = "org.settings"
    form = ff.OrgAmendForm

    def logic(self):
        """
        change your org settings
        """
        forms = self.__class__.form

        org = UserSettings.get_org(self.request.user)

        if self.request.POST:
            form = forms(self.request.POST, instance=org)
            if form.is_valid():
                form.save()
                self.message = "Settings Updated"
                form = forms(instance=org)
        else:
            form = forms(instance=org)

        self.submit_text = "Change Settings"
        self.form = form


class RegisterView(ComboView):
    template = "registration//register.html"
    url_patterns = [r"^register/"]
    url_name = "register"

    def view(self, request):
        if request.POST:
            form = ff.RegisterForm(request.POST)
            if form.is_valid():
                cd = form.cleaned_data
                user = User.objects.create_user(
                    username=cd["email"],
                    email=cd["email"],
                    password=cd["password"],
                    first_name=cd["first_name"],
                    last_name=cd["last_name"],
                )
                norg = Organisation(name=cd["org_name"])
                norg.save()
                user = authenticate(username=cd["email"], password=cd["password"])
                # create the user settings we need
                UserSettings.join(user, norg)
                login(request, user)
                raise RedirectException(reverse("home"))
        else:
            form = ff.RegisterForm()

        return {
            "form": form,
            "title": "Register",
        }


class NewDocView(LoggedInView):
    template = "frontend//new_doc.html"
    url_patterns = [r"^document/new"]
    url_name = "document.new"

    @prelogic
    def new_doc_form_logic(self):
        def short_title(v):
            if ":" in v:
                v1 = v.split(":")[0]
            else:
                v1 = v
            words = v1.split(" ")
            if words[0].lower() == "the":
                words = words[1:]
            return " ".join(words[:3])

        request = self.request
        form = ff.NewDocumentForm

        org = UserSettings.get_org(self.request.user)

        if request.POST:
            new_document_form = form(request.POST)
            if new_document_form.is_valid():
                cd = new_document_form.cleaned_data
                root = slugify(cd["title"])
                short = short_title(cd["title"])
                slug = root
                count = 1
                while Article.objects.filter(slug=slug, org=org).exists():
                    slug = root + "_" + str(count)
                    count += 1
                a = Article(
                    title=cd["title"],
                    short_title=short,
                    slug=slug,
                    org=org,
                )
                a.save()
                if "file" in request.FILES:
                    a.source_file.save(root + ".docx", request.FILES["file"])
                    print("triggering import")
                    a.trigger_source_import()
                    a.save()

        else:
            new_document_form = form()

        self.new_document_form = new_document_form


class ReuploadFormView(ArticleEditBase, LoggedInView):
    template = "frontend//doc_reupload.html"
    url_patterns = [r"^document/([0-9]*)/reupload"]
    url_name = "document.reupload"

    @prelogic
    def new_doc_form_logic(self):
        request = self.request
        form = ff.ReuploadWordForm
        if request.POST:
            new_document_form = form(request.POST)
            if new_document_form.is_valid():
                if "file" in request.FILES:
                    self.article.source_file.save(
                        self.article.slug + ".docx", request.FILES["file"]
                    )
                    print("triggering import")
                    self.article.trigger_source_import()
                    self.article.save()
                    raise RedirectException(
                        reverse("article.settings", args=(self.article.id,))
                    )
        else:
            new_document_form = form()

        self.message = "Warning|Caution! This will override all current text."
        self.new_document_form = new_document_form


class ChangeOrgView(NewDocView):
    url_patterns = [r"^orgs/change/(.*)"]
    url_name = "org.change"
    args = ("org_id",)

    def logic(self):
        new_org = Organisation.objects.get(id=self.org_id)
        UserSettings.change_org(self.request.user, new_org)
        raise RedirectException(reverse("home"))


class HomeView(NewDocView):
    template = "frontend//home.html"
    url_patterns = [r"^"]
    url_name = "home"

    def logic(self):
        org = UserSettings.get_org(self.request.user)
        documents = Article.objects.filter(org=org).order_by("-last_updated")[:10]
        self.documents = documents
        self.orgs = Organisation.objects.all().order_by("name")


class DocListView(HomeView):
    template = "frontend//doc_list.html"
    url_patterns = [r"^documents/list", r"^documents/list/(.*)"]
    url_name = "document.list"
    args = (("page_no", 1),)

    def logic(self):
        page_count = 10
        org = UserSettings.get_org(self.request.user)
        documents = Article.objects.filter(org=org).order_by("-last_updated")
        paginator = GroupedPaginator(documents, page_count)
        page = self.page_no
        try:
            objects = paginator.page(page)
        except PageNotAnInteger:
            objects = paginator.page(1)
        except EmptyPage:
            objects = paginator.page(paginator.num_pages)

        self.documents = objects
