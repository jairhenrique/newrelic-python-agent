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

import logging

import pytest
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


@pytest.mark.parametrize(
    "endpoint,transaction_name", (("/sync", "_target_application:sync"), ("/async", "_target_application:non_sync"))
)
def test_application(caplog, app, endpoint, transaction_name):
    caplog.set_level(logging.ERROR)

    @validate_transaction_metrics(transaction_name, scoped_metrics=[(f"Function/{transaction_name}", 1)])
    @validate_code_level_metrics(*transaction_name.split(":"))
    def _test():
        response = app.get(endpoint)
        assert response.status == 200

        # Catch context propagation error messages
        assert not caplog.records

    _test()
