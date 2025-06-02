# Disabled for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import base64
from datetime import datetime, timezone
import json
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase

from django_gcp.events.utils import decode_pubsub_message, get_event_url, make_pubsub_message

DEFAULT_SUBSCRIPTION = "projects/my-project/subscriptions/my-subscription"


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
            self.assertEqual(event_url, "https://something.com/example-django-gcp/events/the-kind/the-reference")

    def test_make_bare_pubsub_message(self):
        msg = make_pubsub_message({"my": "data"}, DEFAULT_SUBSCRIPTION)
        decoded = json.loads(msg)
        self.assertIn("message", decoded)
        self.assertIn("subscription", decoded)
        self.assertIn("data", decoded["message"])
        self.assertNotIn("publishTime", decoded["message"])
        self.assertNotIn("orderingKey", decoded["message"])
        self.assertNotIn("messageId", decoded["message"])

    def test_make_full_pubsub_message(self):
        dt = datetime(2022, 8, 12, 9, 0, 25, 226743)
        msg = make_pubsub_message(
            {"my": "data"},
            DEFAULT_SUBSCRIPTION,
            attributes={"one": "two"},
            message_id="myid",
            ordering_key="one",
            publish_time=dt,
        )
        decoded = json.loads(msg)
        self.assertIn("message", decoded)
        self.assertIn("subscription", decoded)
        self.assertIn("data", decoded["message"])
        self.assertIn("publishTime", decoded["message"])
        self.assertIn("orderingKey", decoded["message"])
        self.assertIn("messageId", decoded["message"])
        self.assertEqual(decoded["message"]["data"], "eyJteSI6ICJkYXRhIn0=")
        self.assertEqual(decoded["message"]["publishTime"], "2022-08-12T09:00:25.226743000Z")
        self.assertEqual(decoded["message"]["orderingKey"], "one")
        self.assertEqual(decoded["message"]["messageId"], "myid")

    def test_make_pubsub_message_fails_with_invalid_attributes(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                DEFAULT_SUBSCRIPTION,
                attributes={2: "a"},
            )
        self.assertEqual(e.exception.args[0], "All attribute keys must be strings")

        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                DEFAULT_SUBSCRIPTION,
                attributes={"a": 2},
            )
        self.assertEqual(e.exception.args[0], "All attribute values must be strings")

    def test_make_pubsub_message_fails_with_invalid_message_id(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                DEFAULT_SUBSCRIPTION,
                message_id=2,
            )
        self.assertEqual(e.exception.args[0], "The message_id, if given, must be a string")

    def test_make_pubsub_message_fails_with_invalid_ordering_key(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                DEFAULT_SUBSCRIPTION,
                ordering_key=2,
            )
        self.assertEqual(e.exception.args[0], "The ordering_key, if given, must be a string")

    def test_make_pubsub_message_fails_with_invalid_subscription(self):
        with self.assertRaises(ValueError) as e:
            make_pubsub_message(
                {"my": "data"},
                {"subscription-is-not": "a-string"},
            )
        self.assertEqual(
            e.exception.args[0],
            "The subscription must be a string, like 'projects/my-project/subscriptions/my-subscription-name'",
        )

    def test_make_pubsub_message_adjusts_to_utc(self):
        """Ensure that non-naive publish_time datetimes are correctly converted"""

        # LA 7 hours behind UTC at this datetime
        dt = datetime(2022, 8, 12, 9, 0, 25, 226743, tzinfo=ZoneInfo("America/Los_Angeles"))
        utc_dt = datetime(2022, 8, 12, 16, 0, 25, 226743, tzinfo=timezone.utc)

        msg = make_pubsub_message(
            {"my": "data"},
            DEFAULT_SUBSCRIPTION,
            attributes={"one": "two"},
            message_id="myid",
            ordering_key="one",
            publish_time=dt,
        )

        decoded = decode_pubsub_message(msg)

        self.assertEqual(decoded["publish_time"], utc_dt)

    def test_decode_pubsub_message(self):
        dt = datetime(2022, 8, 12, 9, 0, 25, 226743, tzinfo=timezone.utc)
        body = make_pubsub_message(
            {"my": "data"},
            DEFAULT_SUBSCRIPTION,
            attributes={"one": "two"},
            message_id="myid",
            ordering_key="one",
            publish_time=dt,
        )

        decoded = decode_pubsub_message(body)
        self.assertIn("data", decoded)
        self.assertIn("my", decoded["data"])
        self.assertIn("publish_time", decoded)
        self.assertEqual(decoded["publish_time"], dt)

    def test_decode_pubsub_message_with_non_decodable_string_data(self):
        """Test that raw strings in pub/sub messages can be decoded.

        A single string is a valid token in JSON, but it has to be encoded with its quotation marks.
        However, a string that's base-64 encoded directly without being jumped to JSON first is still a valid
        PubSub message.

        That is, endpoints could receive data that's the base 64 encoded verison of:
            b'"stuff"' or
            b'stuff'

        So the decoder has to handle them both the same. We test here that it can.
        """

        body = make_pubsub_message("stuff", DEFAULT_SUBSCRIPTION, as_dict=True)
        body["message"]["data"] = base64.b64encode("stuff".encode()).decode()

        decoded = decode_pubsub_message(body)
        self.assertIn("data", decoded)
        self.assertEqual("stuff", decoded["data"])

    def test_decode_invalid_pubsub_message_raises_value_error(self):
        with self.assertRaises(ValueError) as e:
            body = json.dumps({"has_no_message": {}, "or_subscription": {}}).encode("utf-8")
            decode_pubsub_message(body)

        self.assertIn("Failed to decode Pub/Sub message", e.exception.args[0])
