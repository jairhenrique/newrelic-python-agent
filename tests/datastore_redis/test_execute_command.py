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
import redis
from testing_support.db_settings import redis_settings
from testing_support.fixtures import override_application_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = redis_settings()[0]
REDIS_PY_VERSION = get_package_version_tuple("redis")


# Settings

_enable_instance_settings = {"datastore_tracer.instance_reporting.enabled": True}
_disable_instance_settings = {"datastore_tracer.instance_reporting.enabled": False}

# Metrics

_base_scoped_metrics = [("Datastore/operation/Redis/client_list", 1)]
if REDIS_PY_VERSION >= (5, 0):
    _base_scoped_metrics.append(("Datastore/operation/Redis/client_setinfo", 2))

_base_rollup_metrics = [
    ("Datastore/all", 3),
    ("Datastore/allOther", 3),
    ("Datastore/Redis/all", 3),
    ("Datastore/Redis/allOther", 3),
    ("Datastore/operation/Redis/client_list", 1),
]
if REDIS_PY_VERSION >= (5, 0):
    _base_rollup_metrics.append(("Datastore/operation/Redis/client_setinfo", 2))

_host = instance_hostname(DB_SETTINGS["host"])
_port = DB_SETTINGS["port"]

_instance_metric_name = f"Datastore/instance/Redis/{_host}/{_port}"

instance_metric_count = 3 if REDIS_PY_VERSION >= (5, 0) else 1

_enable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, instance_metric_count))

_disable_rollup_metrics = _base_rollup_metrics.append((_instance_metric_name, None))


def exercise_redis_multi_args(client):
    client.execute_command("CLIENT", "LIST", parse="LIST")


def exercise_redis_single_arg(client):
    client.execute_command("CLIENT LIST")


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_two_args_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_two_args_enable():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_two_args_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_two_args_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_two_args_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_execute_command_two_args_enable():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_two_args_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_execute_command_two_args_disabled():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_multi_args(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_as_one_arg_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_as_one_arg_enable():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_strict_redis_execute_command_as_one_arg_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_strict_redis_execute_command_as_one_arg_disabled():
    r = redis.StrictRedis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_enable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_as_one_arg_enable",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_enable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_execute_command_as_one_arg_enable():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)


@pytest.mark.skipif(REDIS_PY_VERSION < (2, 10), reason="This command is not implemented yet")
@override_application_settings(_disable_instance_settings)
@validate_transaction_metrics(
    "test_execute_command:test_redis_execute_command_as_one_arg_disabled",
    scoped_metrics=_base_scoped_metrics,
    rollup_metrics=_disable_rollup_metrics,
    background_task=True,
)
@background_task()
def test_redis_execute_command_as_one_arg_disabled():
    r = redis.Redis(host=DB_SETTINGS["host"], port=DB_SETTINGS["port"], db=0)
    exercise_redis_single_arg(r)
