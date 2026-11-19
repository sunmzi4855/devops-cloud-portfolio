import json
import unittest
from unittest.mock import Mock

from botocore.exceptions import ClientError

from worker import InvalidEvent, handle_message, parse_event


EVENT = {"event_id": "release-101", "service": "catalog", "revision": "r1"}


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "PutItem")


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.sqs = Mock()
        self.db = Mock()
        self.message = {"Body": json.dumps(EVENT), "ReceiptHandle": "receipt"}

    def process(self):
        return handle_message(self.sqs, "queue", self.db, "deployments", self.message)

    def test_invalid_bodies_never_write_or_acknowledge(self):
        for body in ("{", "[]", "{}", json.dumps({**EVENT, "revision": " "}),
                     json.dumps({**EVENT, "revision": 4}), json.dumps({**EVENT, "extra": "key"})):
            with self.subTest(body=body):
                self.message["Body"] = body
                self.assertEqual(self.process(), "invalid")
        self.db.put_item.assert_not_called()
        self.sqs.delete_message.assert_not_called()

    def test_schema_accepts_an_identifier_boundary(self):
        self.assertEqual(parse_event(json.dumps({**EVENT, "service": "a" * 128}))["service"], "a" * 128)
        with self.assertRaises(InvalidEvent):
            parse_event(json.dumps({**EVENT, "service": "a" * 129}))

    def test_a_successful_write_is_acknowledged(self):
        self.assertEqual(self.process(), "recorded")
        self.assertEqual(self.db.put_item.call_args.kwargs["ConditionExpression"], "attribute_not_exists(event_id)")
        self.sqs.delete_message.assert_called_once_with(QueueUrl="queue", ReceiptHandle="receipt")

    def test_identical_replay_is_acknowledged_after_a_strong_read(self):
        self.db.put_item.side_effect = client_error("ConditionalCheckFailedException")
        self.db.get_item.return_value = {"Item": {k: {"S": v} for k, v in EVENT.items()}}
        self.assertEqual(self.process(), "replay")
        self.assertTrue(self.db.get_item.call_args.kwargs["ConsistentRead"])
        self.sqs.delete_message.assert_called_once()

    def test_conflicting_content_stays_unacknowledged(self):
        self.db.put_item.side_effect = client_error("ConditionalCheckFailedException")
        old = {**EVENT, "revision": "other"}
        self.db.get_item.return_value = {"Item": {k: {"S": v} for k, v in old.items()}}
        self.assertEqual(self.process(), "conflict")
        self.sqs.delete_message.assert_not_called()

    def test_database_outage_can_be_retried(self):
        self.db.put_item.side_effect = client_error("ProvisionedThroughputExceededException")
        with self.assertRaises(ClientError):
            self.process()
        self.sqs.delete_message.assert_not_called()

    def test_missing_prior_record_is_not_acknowledged(self):
        self.db.put_item.side_effect = client_error("ConditionalCheckFailedException")
        self.db.get_item.return_value = {}
        with self.assertRaises(RuntimeError):
            self.process()
        self.sqs.delete_message.assert_not_called()
