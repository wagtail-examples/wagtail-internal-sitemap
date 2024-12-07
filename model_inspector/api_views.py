from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import F, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.views.generic import ListView
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.contrib.redirects.models import Redirect
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Collection, Task, Workflow

from model_inspector.views import filter_exclude_queryset


class ModelInspectorAdminURLFinder(AdminURLFinder):
    def get_listing_url(self, instance):
        if not instance:
            return None

        model = type(instance)

        if model == Workflow:
            return "/admin/workflows/list/"
        elif model == Task:
            return "/admin/workflows/tasks/index/"
        elif model == Collection:
            return "/admin/collections/"
        elif model == Document:
            return "/admin/documents/"
        elif model == Image:
            return "/admin/images/"
        elif model == Redirect:
            return "/admin/redirects/"

        # Fallback to manipluating the admin edit url parts
        try:
            parts = super().get_edit_url(instance).strip("/").split("/")
            try:
                pos = parts.index("edit")
            except ValueError:
                pos = len(parts)

            return f'/{"/".join(parts[:pos])}/'
        except AttributeError:
            return None


admin_url_finder = ModelInspectorAdminURLFinder()


def get_first_instance_url(app_label, model):
    print(app_label, model)
    model_class = apps.get_model(app_label, model)
    instance = model_class.objects.first()
    try:
        return instance.get_url()
    except AttributeError:
        return None


class APIIndexView(ListView):
    # This will return a json response
    # Split the json response into 2 parts
    # Admin results and frontend results
    # Use filter_exclude_queryset if the exclude parameter is passed
    # Otherwise use the queryset
    def get_queryset(self):
        if not self.request.GET.get("exclude"):
            queryset = ContentType.objects.all()
        else:
            queryset = filter_exclude_queryset(queryset)

        queryset = queryset.annotate(
            # get the first record of each model and use the get_url method to get the frontend url
            frontend_url=Concat(
                get_first_instance_url(
                    Value(""),
                    F("app_label"),
                    Value("."),
                    F("model"),
                ),
                output_field=models.CharField(),
            )
        )

        # Annotate the queryset to add the full dotted path and AdminURL to each model
        # for contenttype in queryset:
        #     contenttype.full_dotted_path = f"{contenttype.app_label}.{contenttype.model}"
        # for contenttype in queryset.objects.all():
        #     instance = contenttype.model_class().objects.first()

        #     # SPECIAL CASE: Collection
        #     if isinstance(instance, Collection):
        #         root = Collection.get_first_root_node()
        #         instance = root.get_children().first()

        #     # FRONTEND URL
        #     frontend_instance_url = None
        #     try:
        #         frontend_instance_url = instance.get_url()
        #         contenttype.frontend_url = frontend_instance_url
        #     except AttributeError:
        #         contenttype.frontend_url = None

        #     # ADMIN URL
        #     admin_instance_url = admin_url_finder.get_edit_url(instance)
        #     if admin_instance_url:
        #         contenttype.admin_edit_url = admin_instance_url
        #     else:
        #         contenttype.admin_edit_url = None

        #     # LISTING URL
        #     listing_instance_url = admin_url_finder.get_listing_url(instance)
        #     if listing_instance_url:
        #         contenttype.listing = listing_instance_url
        #     else:
        #         contenttype.listing = None

        #     # ACTIONS
        #     # contenttype.actions = render_to_string(
        #     #     "model_inspector/fragments/check_button.html",
        #     # )

        #     # EXCLUDE
        #     contenttype.exclude = f"{contenttype.app_label}.{contenttype.model}"
        #     # render_to_string(
        #     #     "model_inspector/fragments/copy_button.html",
        #     #     {
        #     #         "app_label": contenttype.app_label,
        #     #         "model": contenttype.model,
        #     #     },
        #     # )

        return queryset

    def render_to_response(self, context, **response_kwargs):
        queryset = self.get_queryset()
        # queryset = [
        #     {
        #         "id": "1234",
        #         "app_label": "1234",
        #         "model": "1234",
        #         "frontend_url": "1234",
        #         "admin_edit_url": "1234",
        #         "listing": "1234",
        #         "exclude": "1234",
        #     }
        # ]
        data = list(queryset.values())
        return JsonResponse(data, safe=False, **response_kwargs)
