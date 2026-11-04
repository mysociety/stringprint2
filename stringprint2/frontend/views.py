from stringprint2.view_framework import (
    RedirectException,
    StringprintView,
    before_logic,
)
from . import forms as ff
from stringprint.models import Article, Organisation
from .models import UserSettings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.paginator import Paginator, Page
from django.core.exceptions import PermissionDenied


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
        h_range = full_range // 2
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


class GroupedPaginator(Paginator):
    def _get_page(self, *args, **kwargs):
        return GroupedPage(*args, **kwargs)


class LoggedInView(StringprintView):
    """Require an authenticated user for legacy management views."""

    view_decorators = (login_required,)

    @before_logic
    def generic(self):
        self.url_name = self.__class__.url_name

    @before_logic
    def get_org(self):
        self.org = UserSettings.get_org(self.request.user)

    def access_denied_no_auth(self, request):
        raise RedirectException(reverse("login"))


class ArticleEditBase(StringprintView):
    """
    article based editing views
    """

    args = ["article_id"]

    @before_logic
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


class ArticlePublishView(ArticleEditBase, LoggedInView):
    """Redirect the retired publish screen to durable operation management."""

    url_patterns = [r"^document/(.*)/publish"]
    url_name = "article.publish"

    def logic(self):
        """Preserve the documented URL without invoking removed queue models."""
        raise RedirectException(
            reverse(
                "publication_management:publication_detail",
                args=(self.article.slug,),
            )
        )


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


class RegisterView(StringprintView):
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
    """
    Send retired browser uploads to the source-backed publication catalog.
    """

    url_patterns = [r"^document/new"]
    url_name = "document.new"

    def logic(self):
        raise RedirectException(reverse("publication_management:publication_list"))


class ReuploadFormView(ArticleEditBase, LoggedInView):
    """
    Preserve old upload links without invoking the removed import queue.
    """

    url_patterns = [r"^document/([0-9]*)/reupload"]
    url_name = "document.reupload"

    def logic(self):
        raise RedirectException(
            reverse(
                "publication_management:publication_detail", args=(self.article.slug,)
            )
        )


class ChangeOrgView(LoggedInView):
    url_patterns = [r"^orgs/change/(.*)"]
    url_name = "org.change"
    args = ("org_id",)

    def logic(self):
        new_org = Organisation.objects.filter(
            id=self.org_id, user_settings__user=self.request.user
        ).first()
        if new_org is None:
            raise PermissionDenied("No membership in the selected organisation")
        UserSettings.change_org(self.request.user, new_org)
        raise RedirectException(reverse("home"))


class HomeView(LoggedInView):
    """
    Redirect the original dashboard to the current management interface.
    """

    url_patterns = [r"^$"]
    url_name = "home"

    def logic(self):
        raise RedirectException(reverse("publication_management:publication_list"))


class DocListView(HomeView):
    template = "frontend//doc_list.html"
    url_patterns = [r"^documents/list", r"^documents/list/(.*)"]
    url_name = "document.list"
    args = (("page_no", 1),)

    def logic(self):
        raise RedirectException(reverse("publication_management:publication_list"))
