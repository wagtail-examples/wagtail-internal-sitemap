from django.conf import settings
from django.templatetags.static import static
from django.urls import include, path, reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail.admin.ui.components import Component

from model_inspector import urls


@hooks.register("insert_global_admin_js")
def copy_script():
    copy_script = format_html(
        '<script src="{0}"></script>',
        static("model_inspector/js/copy.js"),
    )
    check_script = format_html(
        '<script src="{0}"></script>',
        static("model_inspector/js/check.js"),
    )
    return copy_script + check_script


@hooks.register("register_admin_urls")
def register_admin_urls():
    return [
        path("model-inspector/", include(urls, namespace="model_inspector")),
    ]


@hooks.register("register_admin_menu_item")
def register_model_inspector_menu_item():
    return AdminOnlyMenuItem(
        "Model Inspector",
        reverse("model_inspector:index"),
        icon_name="crosshairs",
        order=10000,
    )


class WelcomePanel(Component):
    template_name = "model_inspector/welcome_panel.html"
    order = 500

    def get_context_data(self, parent_context):
        ctx = super().get_context_data(parent_context)
        ctx["settings_present"] = (
            True if hasattr(settings, "MODEL_INSPECTOR_EXCLUDE") else False
        )

        return ctx


@hooks.register("construct_homepage_panels")
def add_another_welcome_panel(request, panels):
    panels.append(WelcomePanel())
