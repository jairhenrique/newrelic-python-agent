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

import os
from io import BytesIO

import asyncpg
import pytest
from testing_support.db_settings import postgresql_settings
from testing_support.util import instance_hostname
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_tt_collector_json import validate_tt_collector_json

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version_tuple

DB_SETTINGS = postgresql_settings()[0]


PG_PREFIX = "Datastore/operation/Postgres/"
ASYNCPG_VERSION = get_package_version_tuple("asyncpg")

if ASYNCPG_VERSION < (0, 11):
    CONNECT_METRICS = ()
else:
    CONNECT_METRICS = ((f"{PG_PREFIX}connect", 1),)


@pytest.fixture
def conn(event_loop):
    conn = event_loop.run_until_complete(
        asyncpg.connect(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
        )
    )
    yield conn
    event_loop.run_until_complete(conn.close())


@validate_transaction_metrics(
    "test_single",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}select", 1),),
    rollup_metrics=(("Datastore/all", 1),),
)
@validate_tt_collector_json(datastore_params={"port_path_or_id": str(DB_SETTINGS["port"])})
@background_task(name="test_single")
@pytest.mark.parametrize("method", ("execute",))
def test_single(event_loop, method, conn):
    assert ASYNCPG_VERSION is not None
    _method = getattr(conn, method)
    event_loop.run_until_complete(_method("""SELECT 0"""))


@validate_transaction_metrics(
    "test_prepared_single",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}prepare", 1), (f"{PG_PREFIX}select", 1)),
    rollup_metrics=(("Datastore/all", 2),),
)
@background_task(name="test_prepared_single")
@pytest.mark.parametrize("method", ("fetch", "fetchrow", "fetchval"))
def test_prepared_single(event_loop, method, conn):
    assert ASYNCPG_VERSION is not None
    _method = getattr(conn, method)
    event_loop.run_until_complete(_method("""SELECT 0"""))


@validate_transaction_metrics(
    "test_prepare",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}prepare", 1),),
    rollup_metrics=(("Datastore/all", 1),),
)
@background_task(name="test_prepare")
def test_prepare(event_loop, conn):
    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(conn.prepare("""SELECT 0"""))


@pytest.fixture
def table(event_loop, conn):
    table_name = f"table_{os.getpid()}"

    event_loop.run_until_complete(conn.execute(f"""create table {table_name} (a integer, b real, c text)"""))

    return table_name


@pytest.mark.skipif(ASYNCPG_VERSION < (0, 11), reason="Copy wasn't implemented before 0.11")
@validate_transaction_metrics(
    "test_copy",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}prepare", 1), (f"{PG_PREFIX}copy", 3)),
    rollup_metrics=(("Datastore/all", 4),),
)
@background_task(name="test_copy")
def test_copy(event_loop, table, conn):
    async def amain():
        await conn.copy_records_to_table(table, records=[(1, 2, "3"), (4, 5, "6")])
        await conn.copy_from_table(table, output=BytesIO())

        # Causes a prepare and copy statement to be executed
        # 2 statements
        await conn.copy_from_query("""SELECT 0""", output=BytesIO())

    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_select_many",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}prepare", 1), (f"{PG_PREFIX}select", 1)),
    rollup_metrics=(("Datastore/all", 2),),
)
@background_task(name="test_select_many")
def test_select_many(event_loop, conn):
    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(conn.executemany("""SELECT $1::int""", ((1,), (2,))))


@validate_transaction_metrics(
    "test_transaction",
    background_task=True,
    scoped_metrics=((f"{PG_PREFIX}begin", 1), (f"{PG_PREFIX}select", 1), (f"{PG_PREFIX}commit", 1)),
    rollup_metrics=(("Datastore/all", 3),),
)
@background_task(name="test_transaction")
def test_transaction(event_loop, conn):
    async def amain():
        async with conn.transaction():
            await conn.execute("""SELECT 0""")

    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(amain())


@validate_transaction_metrics(
    "test_cursor",
    background_task=True,
    scoped_metrics=(
        (f"{PG_PREFIX}begin", 1),
        (f"{PG_PREFIX}prepare", 2),
        (f"{PG_PREFIX}select", 3),
        (f"{PG_PREFIX}commit", 1),
    ),
    rollup_metrics=(("Datastore/all", 7),),
)
@background_task(name="test_cursor")
def test_cursor(event_loop, conn):
    async def amain():
        async with conn.transaction():
            async for _record in conn.cursor("SELECT generate_series(0, 0)", prefetch=1):
                pass

            await conn.cursor("SELECT 0")

    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(amain())


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11),
    reason="This is testing connect behavior which is only captured on newer asyncpg versions",
)
@validate_transaction_metrics(
    "test_unix_socket_connect",
    background_task=True,
    rollup_metrics=[
        (f"Datastore/instance/Postgres/{instance_hostname('localhost')}//.s.PGSQL.THIS_FILE_BETTER_NOT_EXIST", 1)
    ],
)
@background_task(name="test_unix_socket_connect")
def test_unix_socket_connect(event_loop):
    assert ASYNCPG_VERSION is not None
    with pytest.raises(OSError):
        event_loop.run_until_complete(asyncpg.connect("postgres://?host=/.s.PGSQL.THIS_FILE_BETTER_NOT_EXIST"))


@pytest.mark.skipif(
    ASYNCPG_VERSION < (0, 11),
    reason="This is testing connect behavior which is only captured on newer asyncpg versions",
)
@validate_transaction_metrics("test_pool_acquire", background_task=True, scoped_metrics=((f"{PG_PREFIX}connect", 2),))
@background_task(name="test_pool_acquire")
def test_pool_acquire(event_loop):
    async def amain():
        pool = await asyncpg.create_pool(
            user=DB_SETTINGS["user"],
            password=DB_SETTINGS["password"],
            database=DB_SETTINGS["name"],
            host=DB_SETTINGS["host"],
            port=DB_SETTINGS["port"],
            min_size=1,
        )

        try:
            async with pool.acquire():
                async with pool.acquire():
                    pass

        finally:
            await pool.close()

    assert ASYNCPG_VERSION is not None
    event_loop.run_until_complete(amain())
