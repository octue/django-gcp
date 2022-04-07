from django.contrib import admin
from django.urls import include, re_path

from django_gcp import urls as django_gcp_urls


admin.autodiscover()


urlpatterns = [re_path(r"^admin/", admin.site.urls), re_path(r"^test-django-gcp/", include(django_gcp_urls))]
