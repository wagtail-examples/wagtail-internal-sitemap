from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Model
from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.contrib.redirects.models import Redirect
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Collection, Task, Workflow


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


@dataclass
class CType:
    ctype: ContentType
    excluded: bool = False
    dotted_path: str = ""
    model_class: Model = None
    firstInstance: Model = None
    firstInstanceUrl: str = ""

    def __post_init__(self):
        self.excluded = True if self.is_excluded(self.ctype) else False
        self.dotted_path = f"{self.ctype.app_label}.{self.ctype.model}"
        self.model_class = self.ctype.model_class()
        self.firstInstance = self.model_class.objects.first()
        self.firstInstanceUrl = self.get_admin_url()
        if self.firstInstance:
            try:
                self.firstInstanceUrl = self.firstInstance.get_url()
            except AttributeError:
                pass
            try:
                self.firstInstanceUrl = ModelInspectorAdminURLFinder().get_edit_url(
                    self.firstInstance
                )
            except AttributeError:
                pass
        if not self.firstInstanceUrl:
            # SPECIAL CASE: Collection
            if isinstance(self.firstInstance, Collection):
                root = Collection.get_first_root_node()
                self.firstInstance = root.get_children().first()

    def is_excluded(self, ctype: ContentType):
        exclude_list = getattr(settings, "MODEL_INSPECTOR_EXCLUDE", [])
        return (ctype.app_label, ctype.model) in exclude_list

    def get_admin_url(self):
        try:
            return ModelInspectorAdminURLFinder().get_edit_url(self.firstInstance)
        except AttributeError:
            return None

    def get_url(self):
        try:
            return self.firstInstance.get_url()
        except AttributeError:
            return None


@dataclass
class ContentTypes:
    content_types: list[CType] = field(default_factory=list)

    def _excluded(self):
        excluded = []
        for ct in self.content_types:
            if ct.excluded:
                excluded.append(ct)
        return excluded

    def _included(self):
        included = []
        for ct in self.content_types:
            if not ct.excluded:
                included.append(ct)
        return included

    def get_excluded(self):
        return self._excluded()

    def get_included(self):
        return self._included()


class Command(BaseCommand):

    def handle(self, *args, **options):
        exclude = getattr(settings, "MODEL_INSPECTOR_EXCLUDE", [])
        print(("admin", "logentry") in exclude)
        qs = ContentType.objects.all()
        types = ContentTypes()
        for ct in qs:
            types.content_types.append(CType(ctype=ct))

        for ct in types.get_included():
            print(f"{ct.dotted_path} - {ct.firstInstance} - {ct.firstInstanceUrl}")
