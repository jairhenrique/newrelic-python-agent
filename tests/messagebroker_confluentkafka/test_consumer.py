# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from conftest import cache_kafka_consumer_headers
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_distributed_trace_accepted import validate_distributed_trace_accepted
from testing_support.validators.validate_error_event_attributes_outside_transaction import (
    validate_error_event_attributes_outside_transaction,
)
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction
from newrelic.common.object_names import callable_name


def test_custom_metrics(get_consumer_record, topic, expected_broker_metrics):
    custom_metrics = [
        (f"Message/Kafka/Topic/Named/{topic}/Received/Bytes", 1),
        (f"Message/Kafka/Topic/Named/{topic}/Received/Messages", 1),
    ] + expected_broker_metrics

    @validate_transaction_metrics(
        f"Named/{topic}", group="Message/Kafka/Topic", custom_metrics=custom_metrics, background_task=True
    )
    @validate_transaction_count(1)
    def _test():
        get_consumer_record()

    _test()


def test_multiple_transactions(get_consumer_record, topic):
    @validate_transaction_count(2)
    def _test():
        get_consumer_record()
        get_consumer_record()

    _test()


def test_custom_metrics_on_existing_transaction(get_consumer_record, topic, expected_broker_metrics):
    from confluent_kafka import __version__ as version

    @validate_transaction_metrics(
        "test_consumer:test_custom_metrics_on_existing_transaction.<locals>._test",
        custom_metrics=[
            (f"Message/Kafka/Topic/Named/{topic}/Received/Bytes", 1),
            (f"Message/Kafka/Topic/Named/{topic}/Received/Messages", 1),
            (f"Python/MessageBroker/Confluent-Kafka/{version}", 1),
        ]
        + expected_broker_metrics,
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        get_consumer_record()

    _test()


def test_custom_metrics_inactive_transaction(get_consumer_record, topic, expected_missing_broker_metrics):
    @validate_transaction_metrics(
        "test_consumer:test_custom_metrics_inactive_transaction.<locals>._test",
        custom_metrics=[
            (f"Message/Kafka/Topic/Named/{topic}/Received/Bytes", None),
            (f"Message/Kafka/Topic/Named/{topic}/Received/Messages", None),
        ]
        + expected_missing_broker_metrics,
        background_task=True,
    )
    @validate_transaction_count(1)
    @background_task()
    def _test():
        end_of_transaction()
        get_consumer_record()

    _test()


def test_agent_attributes(get_consumer_record):
    @validate_attributes("agent", ["kafka.consume.byteCount"])
    def _test():
        get_consumer_record()

    _test()


def test_consumer_errors(topic, consumer, producer):
    # Close the consumer in order to force poll to raise an exception.
    consumer.close()

    expected_error = RuntimeError

    @reset_core_stats_engine()
    @validate_error_event_attributes_outside_transaction(
        num_errors=1, exact_attrs={"intrinsic": {"error.class": callable_name(expected_error)}, "agent": {}, "user": {}}
    )
    def _test():
        with pytest.raises(expected_error):
            producer.produce(topic, value="A")
            producer.flush()
            while consumer.poll(0.5):
                pass

    _test()


def test_consumer_handled_errors_not_recorded(get_consumer_record):
    # It's important to check that we do not notice the StopIteration error.
    @validate_transaction_errors([])
    def _test():
        get_consumer_record()

    _test()


def test_distributed_tracing_headers(topic, producer, consumer, serialize, expected_broker_metrics):
    # Produce the messages inside a transaction, making sure to close it.
    @validate_transaction_count(1)
    @background_task()
    def _produce():
        producer.produce(topic, key="bar", value=serialize({"foo": 1}))
        producer.flush()

    @validate_transaction_metrics(
        f"Named/{topic}",
        group="Message/Kafka/Topic",
        rollup_metrics=[
            ("Supportability/DistributedTrace/AcceptPayload/Success", None),
            ("Supportability/TraceContext/Accept/Success", 1),
        ]
        + expected_broker_metrics,
        background_task=True,
    )
    @validate_transaction_count(1)
    def _consume():
        @validate_distributed_trace_accepted(transport_type="Kafka")
        @cache_kafka_consumer_headers()
        def _test():
            # Start the transaction but don't exit it.
            # Keep polling until we get the record or the timeout is exceeded.
            timeout = 10
            attempts = 0
            record = None
            while not record and attempts < timeout:
                record = consumer.poll(0.5)
                if not record:
                    attempts += 1
                    continue

        _test()

        # Exit the transaction.
        consumer.poll(0.5)

    _produce()
    _consume()


@pytest.fixture(scope="function")
def expected_broker_metrics(broker, topic):
    return [(f"MessageBroker/Kafka/Nodes/{server}/Consume/{topic}", 1) for server in broker.split(",")]


@pytest.fixture(scope="function")
def expected_missing_broker_metrics(broker, topic):
    return [(f"MessageBroker/Kafka/Nodes/{server}/Consume/{topic}", None) for server in broker.split(",")]
