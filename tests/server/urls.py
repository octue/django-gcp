from django.contrib import admin
from django.urls import include, re_path
from django.views.generic.base import RedirectView

from django_gcp import urls as django_gcp_urls


admin.autodiscover()


urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^example-django-gcp/", include(django_gcp_urls)),
    re_path(r"^", RedirectView.as_view(url="admin/")),
]
