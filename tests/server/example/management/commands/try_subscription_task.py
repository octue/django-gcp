from django.core.management import call_command
from django.core.management.base import BaseCommand

from tests.server.example.tasks import PleaseNotifyMeTask


class Command(BaseCommand):
    """A management command to invoke a subscriber task manually by publishing a message to its topic.
    Intended for use while experimenting in a live environment
    """

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running the create_subscriptions command..."))  # pylint: disable=no-member
        call_command("create_subscriptions")

        # Put a message onto the topic queue for this subscriber
        PleaseNotifyMeTask().publish(data="stuff", attributes={"one": "two"})
        self.stdout.write(
            self.style.SUCCESS(  # pylint: disable=no-member
                "Published PleaseNotifyMeTask message onto topic queue, you should receive it shortly"
            )
        )
