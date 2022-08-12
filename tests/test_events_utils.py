# Disabled for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import datetime
import json
from unittest.mock import patch
from django.test import TestCase
from django_gcp.events.utils import get_event_url, make_pubsub_message


class GCloudEventUtilsTests(TestCase):
    @patch("django_gcp.events.signals.event_received.send")
    def test_get_event_url_with_parameters(self, mock):
        """Ensure that push endpoint URLs can be reversed successfully with parameters that are decoded on receipt"""

        complex_parameter = "://something?> awkward"
        event_url = get_event_url(
            "the-kind", "the-reference", event_parameters={"complex_parameter": complex_parameter}, base_url=""
        )

        response = self.client.post(
            event_url,
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        self.assertIn("sender", mock.call_args.kwargs)
        self.assertIn("event_kind", mock.call_args.kwargs)
        self.assertIn("event_reference", mock.call_args.kwargs)
        self.assertIn("event_payload", mock.call_args.kwargs)
        self.assertIn("event_parameters", mock.call_args.kwargs)
        self.assertIn("complex_parameter", mock.call_args.kwargs["event_parameters"])
        self.assertEqual(mock.call_args.kwargs["event_parameters"]["complex_parameter"], complex_parameter)

    def test_endpoint_with_no_base_url(self):
        """Ensure that an AttributeError is correctly raised when getting an event url with no settings.BASE_URL"""

        with self.assertRaises(AttributeError):
            get_event_url("the-kind", "the-reference")

    def test_endpoint_with_base_url(self):
        """Ensure that an AttributeError is correctly raised when getting an event url with no settings.BASE_URL"""

        with self.settings(BASE_URL="https://something.com"):
            event_url = get_event_url("the-kind", "the-reference")
            self.assertEqual(event_url, "https://something.com/test-django-gcp/events/the-kind/the-reference")

    def test_make_bare_pubsub_message(self):
        msg = make_pubsub_message({"my": "data"})
        self.assertIn("data", msg)

    def test_make_full_pubsub_message(self):
        dt = datetime.datetime(2022, 8, 12, 9, 0, 25, 226743)
        msg = make_pubsub_message(
            {"my": "data"},
            attributes={"one": "two"},
            message_id="myid",
            ordering_key="one",
            publish_time=dt,
        )
        self.assertIn("data", msg)
        self.assertEqual(msg["publishTime"], "2022-08-12T09:00:25.226743000Z")
        self.assertEqual(msg["orderingKey"], "one")
        self.assertEqual(msg["messageId"], "myid")

        # Ensure the message is json dumpable with no special encoder
        serialised_msg = json.dumps(msg)
        self.assertIn('"data": "eyJteSI6ICJkYXRhIn0="', serialised_msg)

    def test_make_pubsub_message_fails_with_invalid_attributes(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                attributes={2: "a"},
            )
        self.assertEqual(e.exception.args[0], "All attribute keys must be strings")

        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                attributes={"a": 2},
            )
        self.assertEqual(e.exception.args[0], "All attribute values must be strings")

    def test_make_pubsub_message_fails_with_invalid_message_id(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                message_id=2,
            )
        self.assertEqual(e.exception.args[0], "The message_id, if given, must be a string")

    def test_make_pubsub_message_fails_with_invalid_ordering_key(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                ordering_key=2,
            )
        self.assertEqual(e.exception.args[0], "The ordering_key, if given, must be a string")
