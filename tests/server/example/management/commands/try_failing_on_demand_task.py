from django.core.management.base import BaseCommand

from tests.server.example.tasks import FailingOnDemandTask


class Command(BaseCommand):
    """A management command to invoke on-demand and subscriber tasks manually
    Intended for use while experimenting in a live environment to see if it works
    """

    def handle(self, *args, **options):
        # # Trigger an on-demand task that should suceed
        # CalculatePriceTask().enqueue()

        # # Trigger an on-demand task that should fail
        FailingOnDemandTask().enqueue(a=1, b=1)
