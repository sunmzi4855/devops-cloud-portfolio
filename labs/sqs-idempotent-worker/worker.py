"""Record a deployment once, even if its SQS event arrives more than once."""

import json
import re

from botocore.exceptions import ClientError


FIELDS = ("event_id", "service", "revision")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class InvalidEvent(ValueError):
    """The body cannot be interpreted as a deployment event."""


def parse_event(body: str) -> dict[str, str]:
    try:
        event = json.loads(body)
    except (ValueError, RecursionError) as error:
        raise InvalidEvent("Expected a JSON object") from error
    if not isinstance(event, dict) or set(event) != set(FIELDS):
        raise InvalidEvent("Expected event_id, service, and revision")
    for name in FIELDS:
        if not isinstance(event[name], str) or not IDENTIFIER.fullmatch(event[name]):
            raise InvalidEvent(f"Invalid identifier in {name}")
    return event


def record_deployment(dynamodb, table: str, event: dict[str, str]) -> str:
    """Only the successful conditional insert creates a deployment record."""
    item = {name: {"S": event[name]} for name in FIELDS}
    try:
        dynamodb.put_item(
            TableName=table,
            Item=item,
            ConditionExpression="attribute_not_exists(event_id)",
        )
        return "recorded"
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    previous = dynamodb.get_item(
        TableName=table, Key={"event_id": item["event_id"]}, ConsistentRead=True
    ).get("Item")
    if previous is None:
        raise RuntimeError("The existing deployment disappeared before comparison")
    if all(previous.get(name) == item[name] for name in FIELDS):
        return "replay"
    return "conflict"


def handle_message(sqs, queue_url: str, dynamodb, table: str, message: dict) -> str:
    """Acknowledge only a durable write or an identical previously recorded event."""
    try:
        event = parse_event(message["Body"])
    except InvalidEvent:
        return "invalid"

    outcome = record_deployment(dynamodb, table, event)
    if outcome in ("recorded", "replay"):
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
    return outcome
