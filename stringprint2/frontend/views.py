"""Account pages and compatibility routes for source-backed publications."""

from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from . import forms
from .models import UserSettings
from stringprint2.stringprint.models import Article, Organisation


class LoggedInView(LoginRequiredMixin, TemplateView):
    http_method_names = ["get", "head", "options"]

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            org=UserSettings.get_org(self.request.user),
            url_name=self.request.resolver_match.url_name,
            **kwargs,
        )


class ArticleView(LoggedInView):
    """Resolve a publication within the current user's organisation."""

    def get(self, request, article_id):
        org = UserSettings.get_org(request.user)
        self.article = Article.objects.filter(pk=article_id, org=org).first()
        if self.article is None:
            return redirect("home")
        return self.respond()

    def respond(self):
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(article=self.article, **kwargs)
        if self.article.reprocessing():
            context.update(
                message="This document is currently being processed. "
                "You will be able to see changes in a few minutes.",
                refresh=True,
            )
        return context


class ArticleHeadersView(ArticleView):
    template_name = "frontend/doc_headers.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            header=self.article.images.filter(title_image=True).first(), **kwargs
        )


class ArticleSettingsView(ArticleView):
    template_name = "frontend/document_settings.html"

    def get_context_data(self, **kwargs):
        form = forms.ArticleEditForm(instance=self.article)
        for field in form.fields.values():
            field.disabled = True
        return super().get_context_data(form=form, **kwargs)


class OrgSettingsView(LoggedInView):
    template_name = "frontend/org_amend.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = forms.OrgAmendForm(instance=context["org"])
        for field in form.fields.values():
            field.disabled = True
        context["form"] = form
        return context


class RegisterView(FormView):
    template_name = "registration/register.html"
    form_class = forms.RegisterForm
    success_url = reverse_lazy("home")
    extra_context = {"title": "Register"}

    @transaction.atomic
    def form_valid(self, form):
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        org = Organisation.objects.create(name=data["org_name"])
        UserSettings.join(user, org)
        user = authenticate(username=data["email"], password=data["password"])
        login(self.request, user)
        return super().form_valid(form)


class PublicationRedirectView(ArticleView):
    """Preserve retired publish/upload links to publication management."""

    http_method_names = ["get", "head", "post", "options"]

    def respond(self):
        return redirect("publication_management:publication_detail", self.article.slug)

    post = ArticleView.get


class CatalogRedirectView(LoggedInView):
    http_method_names = ["get", "head", "post", "options"]

    def get(self, request, **kwargs):
        UserSettings.get_org(request.user)
        return redirect("publication_management:publication_list")

    post = get


class ChangeOrgView(LoggedInView):
    http_method_names = ["get", "head", "post", "options"]

    def get(self, request, org_id):
        org = Organisation.objects.filter(
            pk=org_id, user_settings__user=request.user
        ).first()
        if org is None:
            raise PermissionDenied("No membership in the selected organisation")
        UserSettings.change_org(request.user, org)
        return redirect("home")

    post = get
