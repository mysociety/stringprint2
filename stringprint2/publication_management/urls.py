"""URLs for authenticated publication operation management."""

from django.urls import path

from publication_management import views

app_name = "publication_management"

urlpatterns = [
    path("", views.publication_list, name="publication_list"),
    path("operations/", views.operation_list, name="operation_list"),
    path(
        "operations/<int:operation_id>/",
        views.operation_detail,
        name="operation_detail",
    ),
    path(
        "operations/<int:operation_id>/cancel/",
        views.cancel_operation,
        name="cancel_operation",
    ),
    path(
        "publications/<slug:publication_slug>/",
        views.publication_detail,
        name="publication_detail",
    ),
    path(
        "publications/<slug:publication_slug>/<str:operation_name>/",
        views.create_operation,
        name="create_operation",
    ),
]
