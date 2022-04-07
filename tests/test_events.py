# Disabled for testing:
# pylint: disable=missing-docstring
# pylint: disable=protected-access
# pylint: disable=too-many-public-methods

# Disabled because gcloud api dynamically constructed
# pylint: disable=no-member

import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse


class GCloudEventTests(TestCase):
    @patch("django_gcp.events.signals.event_received.send")
    def test_valid_event_is_signalled(self, mock):
        """Ensure a signal is dispatched with the event details"""

        payload = {"the-event": "payload"}
        response = self.client.post(
            reverse("gcp-events", args=["the-event-kind", "the-event-reference"]),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        self.assertIn("sender", mock.call_args.kwargs)
        self.assertIn("event_kind", mock.call_args.kwargs)
        self.assertIn("event_reference", mock.call_args.kwargs)
        self.assertIn("event_payload", mock.call_args.kwargs)

    def test_post_with_no_reference(self):
        """Ensure that posts with no reference will be Not Found"""
        endpoint = reverse("gcp-events", args=["the-event-kind", "anything"]).replace("anything", "")
        response = self.client.post(
            endpoint,
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_non_post_http_methods_disallowed(self):
        """Ensure that methods other than POST are not allowed"""
        endpoint = reverse("gcp-events", args=["the-event-kind", "the-event-reference"])
        response = self.client.get(
            endpoint,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 405)
