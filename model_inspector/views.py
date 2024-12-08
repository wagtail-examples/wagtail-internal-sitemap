import django_filters
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms import CheckboxSelectMultiple
from django.template.loader import render_to_string
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.ui.tables import Column
from wagtail.admin.views import generic
from wagtail.admin.widgets.button import HeaderButton
from wagtail.contrib.redirects.models import Redirect
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Collection, Task, Workflow


def filter_exclude_queryset(qs=None):
    # adding this here so it can be used across the IndexView and the FilterSet
    if not qs:
        qs = ContentType.objects.all()

    if (
        hasattr(settings, "MODEL_INSPECTOR_EXCLUDE")
        and settings.MODEL_INSPECTOR_EXCLUDE
    ):
        exclude_app_model = settings.MODEL_INSPECTOR_EXCLUDE
        return qs.exclude(
            app_label__in=[app_label for app_label, _ in exclude_app_model],
            model__in=[model for _, model in exclude_app_model],
        )
    else:
        return qs

    # if hasattr(settings, "MODEL_INSPECTOR_EXCLUDE") and settings.MODEL_INSPECTOR_EXCLUDE and qs is None:
    #     exclude_app_model = settings.MODEL_INSPECTOR_EXCLUDE
    #     return ContentType.objects.exclude(
    #         app_label__in=[app_label for app_label, _ in exclude_app_model],
    #         model__in=[model for _, model in exclude_app_model],
    #     )
    # elif qs is not None:
    #     exclude_app_model = settings.MODEL_INSPECTOR_EXCLUDE
    #     return qs.exclude(
    #         app_label__in=[app_label for app_label, _ in exclude_app_model],
    #         model__in=[model for _, model in exclude_app_model],
    #     )
    # else:

    # return ContentType.objects.all()


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


class IndexViewFilterSet(WagtailFilterSet):
    app_label = django_filters.MultipleChoiceFilter(
        field_name="app_label",
        lookup_expr="iexact",
        widget=CheckboxSelectMultiple,
        label=_("App label"),
    )
    model = django_filters.MultipleChoiceFilter(
        field_name="model",
        lookup_expr="iexact",
        widget=CheckboxSelectMultiple,
        label=_("Model"),
    )

    class Meta:
        model = ContentType
        fields = []

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data=data, queryset=queryset, request=request, prefix=prefix)

        if not self.request.GET.get("exclude"):
            self.filters["app_label"].extra["choices"] = sorted(
                {(ct.app_label, ct.app_label) for ct in self.queryset}
            )

            self.filters["model"].extra["choices"] = sorted(
                [(ct.model, ct.model) for ct in self.queryset]
            )
        else:
            self.filters["app_label"].extra["choices"] = sorted(
                {(ct.app_label, ct.app_label) for ct in filter_exclude_queryset()}
            )

            self.filters["model"].extra["choices"] = sorted(
                [(ct.model, ct.model) for ct in filter_exclude_queryset()]
            )


class IndexView(generic.IndexView):
    page_title = _("Model Inspector")
    default_ordering = "model"
    filterset_class = IndexViewFilterSet
    header_icon = "crosshairs"
    index_url_name = "model_inspector_index"
    index_results_url_name = "model_inspector_index_results"
    model = ContentType
    search_fields = ["app_label", "model"]
    paginate_by = 50
    table_classname = "model-inspector listing"

    columns = [
        Column("model", label=_("Model"), sort_key="model"),
        Column("admin_edit_url", label=_("Admin Page")),
        Column("frontend_url", label=_("Frontend Page")),
        Column("listing", label=_("Listing Page")),
        Column("actions", label=_("Actions"), classname="check-actions"),
        Column("exclude", label=_("MODEL_INSPECTOR_EXCLUDE entry to hide this model")),
        Column("app_label", label=_("App label"), sort_key="app_label"),
    ]

    @cached_property
    def header_buttons(self):
        buttons = super().header_buttons

        if (
            hasattr(settings, "MODEL_INSPECTOR_EXCLUDE")
            and settings.MODEL_INSPECTOR_EXCLUDE
        ):
            exclude = self.request.GET.get("exclude", None) == "true"

            if exclude:
                label = _("Show All")
                show_all_url = "/admin/model-inspector"
                icon = "cross"
            else:
                label = _("Hide Excluded")
                show_all_url = "/admin/model-inspector?exclude=true"
                icon = "glasses"

            buttons.append(
                HeaderButton(
                    label=label,
                    url=show_all_url,
                    attrs={"data-show-all": True},
                    icon_name=icon,
                )
            )

        return buttons

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.GET.get("exclude"):
            return qs
        else:
            return filter_exclude_queryset(qs)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        for contenttype in ctx["object_list"]:

            # ACTIONS
            contenttype.actions = render_to_string(
                "model_inspector/fragments/check_button.html",
            )

            # EXCLUDE
            contenttype.exclude = render_to_string(
                "model_inspector/fragments/copy_button.html",
                {
                    "app_label": contenttype.app_label,
                    "model": contenttype.model,
                },
            )

            # Get the first instance of the model
            instance = contenttype.model_class().objects.first()

            # SPECIAL CASE: Settings
            # Only the admin url makes sense for settings
            # Single out the settings models using the base classes
            bases = [base.__name__ for base in type(instance).__bases__]
            if "BaseGenericSetting" in bases or "BaseSiteSetting" in bases:
                # There is a redirect to the settings page that should be used
                # so dont' need a instance to work with settings
                admin_instance_url = (
                    f"""/admin/settings/{contenttype.app_label}/{contenttype.model}/"""
                )
                # FRONTEND URL
                contenttype.frontend_url = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )
                # LISTING URL
                contenttype.listing = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )
                # ADMIN URL
                contenttype.admin_edit_url = render_to_string(
                    "model_inspector/fragments/link_secondary.html",
                    {"url": admin_instance_url},
                )

                continue

            # SPECIAL CASE: Collection get the correct instance
            if isinstance(instance, Collection):
                root = Collection.get_first_root_node()
                instance = root.get_children().first()

                # ADMIN URL
                admin_instance_url = admin_url_finder.get_edit_url(instance)
                if admin_instance_url:
                    contenttype.admin_edit_url = render_to_string(
                        "model_inspector/fragments/link_secondary.html",
                        {"url": admin_instance_url},
                    )
                else:
                    contenttype.admin_edit_url = render_to_string(
                        "model_inspector/fragments/does_not_exist.html",
                    )

                # FRONTEND URL
                contenttype.frontend_url = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )

                # LISTING URL
                listing_instance_url = admin_url_finder.get_listing_url(instance)
                if listing_instance_url:
                    contenttype.listing = render_to_string(
                        "model_inspector/fragments/link_secondary.html",
                        {"url": listing_instance_url},
                    )
                else:
                    contenttype.listing = render_to_string(
                        "model_inspector/fragments/does_not_exist.html",
                    )

                continue

            # FRONTEND URL
            frontend_instance_url = None
            try:
                frontend_instance_url = instance.get_url()
                contenttype.frontend_url = render_to_string(
                    "model_inspector/fragments/link_secondary.html",
                    {"url": frontend_instance_url},
                )
            except AttributeError:
                contenttype.frontend_url = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )

            # ADMIN URL
            admin_instance_url = admin_url_finder.get_edit_url(instance)
            if admin_instance_url:
                contenttype.admin_edit_url = render_to_string(
                    "model_inspector/fragments/link_secondary.html",
                    {"url": admin_instance_url},
                )
            else:
                contenttype.admin_edit_url = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )

            # LISTING URL
            listing_instance_url = admin_url_finder.get_listing_url(instance)
            if listing_instance_url:
                contenttype.listing = render_to_string(
                    "model_inspector/fragments/link_secondary.html",
                    {"url": listing_instance_url},
                )
            else:
                contenttype.listing = render_to_string(
                    "model_inspector/fragments/does_not_exist.html",
                )

        return ctx
