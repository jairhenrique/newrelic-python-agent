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

import json

from newrelic.common.encoding_utils import json_encode
from newrelic.common.object_wrapper import transient_function_wrapper


def validate_error_event_collector_json(num_errors=1):
    """Validate the format, types and number of errors of the data we
    send to the collector for harvest.
    """

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_event_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            samples = list(instance.error_events)
            s_info = instance.error_events.sampling_info
            agent_run_id = 666

            # emulate the payload used in data_collector.py

            payload = (agent_run_id, s_info, samples)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            assert decoded_json[0] == agent_run_id

            sampling_info = decoded_json[1]

            harvest_config = instance.settings.event_harvest_config
            reservoir_size = harvest_config.harvest_limits.error_event_data

            assert sampling_info["reservoir_size"] == reservoir_size
            assert sampling_info["events_seen"] == num_errors

            error_events = decoded_json[2]

            assert len(error_events) == num_errors
            for event in error_events:
                # event is an array containing intrinsics, user-attributes,
                # and agent-attributes

                assert len(event) == 3
                for d in event:
                    assert isinstance(d, dict)

        return result

    return _validate_error_event_collector_json
