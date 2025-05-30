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

import uuid

import botocore.session
from moto import mock_aws
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_tt_segment_params import validate_tt_segment_params

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

MOTO_VERSION = get_package_version_tuple("moto")
AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"
AWS_REGION = "us-east-1"
UBUNTU_14_04_PARAVIRTUAL_AMI = "ami-c65be9ae"

TEST_INSTANCE = f"python-agent-test-{uuid.uuid4()}"

_ec2_scoped_metrics = [("External/ec2.us-east-1.amazonaws.com/botocore/POST", 3)]

_ec2_rollup_metrics = [
    ("External/all", 3),
    ("External/allOther", 3),
    ("External/ec2.us-east-1.amazonaws.com/all", 3),
    ("External/ec2.us-east-1.amazonaws.com/botocore/POST", 3),
]


@dt_enabled
@validate_span_events(expected_agents=("aws.requestId",), count=3)
@validate_span_events(exact_agents={"aws.operation": "RunInstances"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "DescribeInstances"}, count=1)
@validate_span_events(exact_agents={"aws.operation": "TerminateInstances"}, count=1)
@validate_tt_segment_params(present_params=("aws.requestId",))
@validate_transaction_metrics(
    "test_botocore_ec2:test_ec2",
    scoped_metrics=_ec2_scoped_metrics,
    rollup_metrics=_ec2_rollup_metrics,
    background_task=True,
)
@background_task()
@mock_aws
def test_ec2():
    session = botocore.session.get_session()
    client = session.create_client(
        "ec2", region_name=AWS_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    # Create instance
    resp = client.run_instances(ImageId=UBUNTU_14_04_PARAVIRTUAL_AMI, InstanceType="m1.small", MinCount=1, MaxCount=1)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["Instances"]) == 1
    instance_id = resp["Instances"][0]["InstanceId"]

    # Describe instance
    resp = client.describe_instances(InstanceIds=[instance_id])
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["Reservations"][0]["Instances"][0]["InstanceId"] == instance_id

    # Delete instance
    resp = client.terminate_instances(InstanceIds=[instance_id])
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TerminatingInstances"][0]["InstanceId"] == instance_id
