"""Run the replay and dead-letter drill against two loopback-only services."""

import json
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from threading import Barrier
from unittest.mock import patch

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from worker import handle_message


BURST = 8
MAX_RECEIVES = 3
FIRST = {"event_id": "release-101", "service": "catalog", "revision": "r1"}
SECOND = {"event_id": "release-102", "service": "search", "revision": "r2"}
THIRD = {"event_id": "release-103", "service": "reports", "revision": "r3"}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


@dataclass
class Lab:
    sqs: BaseClient
    db: BaseClient
    queue: str
    dlq: str
    table: str

    def process(self, message):
        return handle_message(self.sqs, self.queue, self.db, self.table, message)


def wait_for_services(sqs, db):
    deadline = time.monotonic() + 60
    while True:
        try:
            sqs.list_queues()
            db.list_tables(Limit=1)
            return
        except (BotoCoreError, ClientError) as error:
            if time.monotonic() >= deadline:
                raise RuntimeError("Local SQS or DynamoDB did not become ready") from error
            time.sleep(1)


@contextmanager
def isolated_lab():
    session = boto3.Session(
        aws_access_key_id="local", aws_secret_access_key="local", region_name="us-east-1"
    )
    config = Config(connect_timeout=2, read_timeout=5, retries={"total_max_attempts": 2})
    sqs = session.client("sqs", endpoint_url="http://127.0.0.1:9324", config=config)
    db = session.client("dynamodb", endpoint_url="http://127.0.0.1:8000", config=config)
    tag = f"replay-{uuid.uuid4().hex[:12]}"
    with ExitStack() as cleanup:
        cleanup.callback(sqs.close)
        cleanup.callback(db.close)
        wait_for_services(sqs, db)
        dlq = sqs.create_queue(QueueName=f"{tag}-dead")["QueueUrl"]
        cleanup.callback(sqs.delete_queue, QueueUrl=dlq)
        arn = sqs.get_queue_attributes(QueueUrl=dlq, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        policy = {"deadLetterTargetArn": arn, "maxReceiveCount": str(MAX_RECEIVES)}
        queue = sqs.create_queue(
            QueueName=tag, Attributes={"VisibilityTimeout": "1", "RedrivePolicy": json.dumps(policy)}
        )["QueueUrl"]
        cleanup.callback(sqs.delete_queue, QueueUrl=queue)
        db.create_table(
            TableName=tag,
            KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "event_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        cleanup.callback(db.delete_table, TableName=tag)
        db.get_waiter("table_exists").wait(TableName=tag, WaiterConfig={"Delay": 1, "MaxAttempts": 30})
        yield Lab(sqs, db, queue, dlq, tag)


def receive(sqs, url, *, limit=1, wait=1, visibility=None):
    options = {"VisibilityTimeout": visibility} if visibility is not None else {}
    return sqs.receive_message(
        QueueUrl=url, MaxNumberOfMessages=limit, WaitTimeSeconds=wait,
        AttributeNames=["ApproximateReceiveCount"], **options
    ).get("Messages", [])


def next_message(sqs, url):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        batch = receive(sqs, url)
        if batch:
            return batch[0]
    raise TimeoutError("Timed out waiting for a message")


def verify_crash_recovery(lab):
    lab.sqs.send_message(QueueUrl=lab.queue, MessageBody=json.dumps(FIRST))
    first = next_message(lab.sqs, lab.queue)
    # Interrupt only the acknowledgement. The queue and database remain real services.
    with patch.object(lab.sqs, "delete_message", side_effect=InterruptedError("worker stopped")) as ack:
        try:
            lab.process(first)
        except InterruptedError:
            ack.assert_called_once()
        else:
            raise AssertionError("The crash injection did not reach the acknowledgement")
    item = lab.db.get_item(
        TableName=lab.table, Key={"event_id": {"S": FIRST["event_id"]}}, ConsistentRead=True
    ).get("Item")
    check(item is not None and item["revision"]["S"] == FIRST["revision"], "Write was not durable before the crash")

    second = next_message(lab.sqs, lab.queue)
    check(first["MessageId"] == second["MessageId"], "Expected the same queue message after visibility expired")
    count = int(second["Attributes"]["ApproximateReceiveCount"])
    check(count >= 2 and lab.process(second) == "replay", "Redelivery was not recognized and acknowledged")
    return count


def verify_concurrent_duplicates(lab):
    body = json.dumps(SECOND)
    entries = [{"Id": str(n), "MessageBody": body} for n in range(BURST)]
    sent = lab.sqs.send_message_batch(QueueUrl=lab.queue, Entries=entries)
    expected_ids = {entry["MessageId"] for entry in sent["Successful"]}
    check(not sent.get("Failed") and len(expected_ids) == BURST, "Expected eight independently sent messages")
    receipts = {}
    deadline = time.monotonic() + 20
    while len(receipts) < BURST and time.monotonic() < deadline:
        for msg in receive(lab.sqs, lab.queue, limit=10, visibility=60):
            check(msg["MessageId"] in expected_ids, "Unexpected message during the burst")
            receipts[msg["MessageId"]] = msg
    check(receipts.keys() == expected_ids, "Some burst deliveries were missing")

    gate = Barrier(BURST, timeout=15)

    def process_together(msg):
        gate.wait()
        return lab.process(msg)

    with ThreadPoolExecutor(max_workers=BURST) as pool:
        outcomes = Counter(pool.map(process_together, receipts.values()))
    check(outcomes == {"recorded": 1, "replay": BURST - 1}, f"Unexpected burst outcomes: {outcomes}")
    return outcomes


def verify_dead_letters(lab):
    conflict = json.dumps({**FIRST, "revision": "different-revision"})
    incomplete = json.dumps({"event_id": THIRD["event_id"], "service": THIRD["service"]})
    expected = {conflict: "conflict", incomplete: "invalid"}
    attempts = {body: [] for body in expected}
    for body in expected:
        lab.sqs.send_message(QueueUrl=lab.queue, MessageBody=body)

    quarantined = {}
    deadline = time.monotonic() + 45
    while len(quarantined) < len(expected) and time.monotonic() < deadline:
        for msg in receive(lab.sqs, lab.queue, limit=10):
            body = msg["Body"]
            check(body in expected and lab.process(msg) == expected[body], "Bad event was accepted")
            attempts[body].append(int(msg["Attributes"]["ApproximateReceiveCount"]))
        for msg in receive(lab.sqs, lab.dlq, limit=10, wait=0, visibility=60):
            check(msg["Body"] in expected, "Unexpected dead-letter payload")
            quarantined[msg["Body"]] = msg
    check(quarantined.keys() == expected.keys(), "Both messages must reach the broker's dead-letter queue")
    for counts in attempts.values():
        check(counts == list(range(1, MAX_RECEIVES + 1)), f"Unexpected source delivery counts: {counts}")

    # The synthetic release fixture supplies the missing revision. Keep the conflict for review.
    repaired = {**json.loads(quarantined[incomplete]["Body"]), "revision": THIRD["revision"]}
    lab.sqs.send_message(QueueUrl=lab.queue, MessageBody=json.dumps(repaired))
    check(lab.process(next_message(lab.sqs, lab.queue)) == "recorded", "Corrected replay failed")
    lab.sqs.delete_message(QueueUrl=lab.dlq, ReceiptHandle=quarantined[incomplete]["ReceiptHandle"])
    lab.sqs.change_message_visibility(
        QueueUrl=lab.dlq, ReceiptHandle=quarantined[conflict]["ReceiptHandle"], VisibilityTimeout=0
    )
    check(next_message(lab.sqs, lab.dlq)["Body"] == conflict, "The conflict should remain available for review")
    return len(quarantined), attempts[conflict], attempts[incomplete]


def verify_ledger(lab):
    rows = lab.db.scan(TableName=lab.table, ConsistentRead=True)["Items"]
    actual = {row["event_id"]["S"]: {key: value["S"] for key, value in row.items()} for row in rows}
    expected = {event["event_id"]: event for event in (FIRST, SECOND, THIRD)}
    check(actual == expected, f"Final ledger differs from the three expected deployments: {actual}")
    return len(actual)


def main():
    with isolated_lab() as lab:
        crash_count = verify_crash_recovery(lab)
        burst = verify_concurrent_duplicates(lab)
        quarantined, conflict_counts, invalid_counts = verify_dead_letters(lab)
        ledger_count = verify_ledger(lab)
    print("## SQS worker replay and recovery")
    print()
    print("| Check | Observed result |")
    print("| --- | --- |")
    print(f"| Unacknowledged message | Same message returned on delivery {crash_count} and was acknowledged as a replay |")
    print(f"| {BURST} concurrent deliveries for one event | {burst['recorded']} new record, {burst['replay']} replays |")
    print(f"| Conflicting and invalid events | {quarantined} messages reached the dead-letter queue |")
    print(f"| Source deliveries before quarantine | Conflict {conflict_counts}, invalid {invalid_counts} |")
    print("| Selective replay | Corrected message recorded, original conflict retained for review |")
    print(f"| Final DynamoDB ledger | {ledger_count} expected records with their original values |")


if __name__ == "__main__":
    main()
