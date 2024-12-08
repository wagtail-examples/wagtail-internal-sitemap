from django.db import models
from wagtail.contrib.settings.models import (
    BaseGenericSetting,
    BaseSiteSetting,
    register_setting,
)


@register_setting
class GenericSocialMediaSettings(BaseGenericSetting):
    facebook = models.URLField()


@register_setting
class SiteSpecificSocialMediaSettings(BaseSiteSetting):
    facebook = models.URLField()
