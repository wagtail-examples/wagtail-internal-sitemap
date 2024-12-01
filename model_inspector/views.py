import django_filters
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms import CheckboxSelectMultiple
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.ui.tables import Column
from wagtail.admin.views import generic
from wagtail.models import Collection

admin_url_finder = AdminURLFinder()


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

        self.filters["app_label"].extra["choices"] = sorted(
            {(ct.app_label, ct.app_label) for ct in self.queryset}
        )

        self.filters["model"].extra["choices"] = sorted(
            [(ct.model, ct.model) for ct in self.queryset]
        )


class IndexView(generic.IndexView):
    page_title = _("Model Inspector")
    default_ordering = ["app_label", "model"]
    filterset_class = IndexViewFilterSet
    header_icon = "crosshairs"
    index_url_name = "model_inspector:index"
    index_results_url_name = "model_inspector:index_results"
    model = ContentType
    search_fields = [
        "app_label",
        "model",
    ]

    columns = [
        Column(
            "app_label",
            label=_("App label"),
            sort_key="app_label",
        ),
        Column(
            "model",
            label=_("Model"),
            sort_key="model",
        ),
        Column(
            "exclude",
            label=_("exclude_app_model - entry"),
        ),
        Column(
            "frontend_url",
            label=_("Frontend"),
        ),
        Column(
            "admin_edit_url",
            label=_("Admin"),
        ),
        Column(
            "listing",
            label=_("Listing"),
        ),
    ]

    def get_base_queryset(self):
        if hasattr(settings, "MODEL_INSPECTOR_EXCLUDE"):
            exclude_app_model = settings.MODEL_INSPECTOR_EXCLUDE
            return ContentType.objects.exclude(
                app_label__in=[app_label for app_label, _ in exclude_app_model],
                model__in=[model for _, model in exclude_app_model],
            )
        return ContentType.objects.all()

    def get_listing_url(self, admin_instance_url):
        # print(admin_instance_url)
        if not admin_instance_url:
            return None

        # Split the url parts and get the number of parts
        # so they can be rejoined to get the listing url
        parts = admin_instance_url.strip("/").split("/")
        try:
            pos = parts.index("edit")
        except ValueError:
            pos = len(parts)
        print(pos)
        # if not
        if "edit" in parts:
            # e.g. /admin/pages/1/edit/ becomes /admin/pages/
            admin_instance_url = f'/{"/".join(parts[:pos])}/'
        else:
            # e.g. /admin/pages/1/ becomes /admin/pages/
            admin_instance_url = f'/{"/".join(parts[:pos-1])}/'
        return admin_instance_url

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        for contenttype in ctx["object_list"]:
            instance = contenttype.model_class().objects.first()
            secondary_button_class = "button button-small button-secondary"
            primary_button_class = "button button-small button-primary"

            # SPECIAL CASE: Collection
            if isinstance(instance, Collection):
                root = Collection.get_first_root_node()
                instance = root.get_children().first()

            # FRONTEND URL
            try:
                instance_url = instance.get_url()
                contenttype.frontend_url = mark_safe(
                    f'<a href="{instance_url}" class="{primary_button_class}">View Frontend Page</a>'
                )
            except AttributeError:
                contenttype.frontend_url = mark_safe(
                    f'<span class="{secondary_button_class}" disabled>Not available</span>'
                )

            # ADMIN URL
            admin_instance_url = admin_url_finder.get_edit_url(instance)
            if admin_instance_url:
                contenttype.admin_edit_url = mark_safe(
                    f'<a href="{admin_instance_url}" class="{primary_button_class}">View Admin Edit Page</a>'
                )
            else:
                contenttype.admin_edit_url = mark_safe(
                    f'<span class="{secondary_button_class}" disabled>Not available</span>'
                )

            # LISTING URL
            listing_instance_url = self.get_listing_url(admin_instance_url)
            if listing_instance_url:
                contenttype.listing = mark_safe(
                    f'<a href="{listing_instance_url}" class="{primary_button_class}">View Admin Listing Page</a>'
                )
            else:
                contenttype.listing = mark_safe(
                    f'<span class="{secondary_button_class} button_class" disabled>Not available</span>'
                )

            contenttype.exclude = mark_safe(
                mark_safe(
                    f"""
                    <button
                    class="button button-small bicolor button--icon"
                    type="button"
                    data-model-inspector-copy
                    onclick="copyToClipboard(this)">
                        <span class="icon-wrapper">
                            <svg class="icon icon-copy icon" aria-hidden="true">
                                <use href="#icon-copy"></use>
                            </svg>
                        </span>
                        <span class="code">{f'("{contenttype.app_label}", "{contenttype.model}")'}</span>
                    </button>
                    """
                )
            )

        return ctx
