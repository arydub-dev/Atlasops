"""Probe native Redis/ARQ enqueue, retry and result handling in staging only.

ENVIRONMENT=staging REDIS_URL=<secret rediss URL> backend/.venv/bin/python scripts/verify_queue.py
Uses a unique queue; never consumes application jobs or flushes a database.
"""
import asyncio
import os
from uuid import uuid4
from urllib.parse import urlsplit

from arq import create_pool, Retry
from arq.connections import RedisSettings
from arq.worker import Worker


async def pilot_probe(ctx, value):
    if ctx['job_try'] == 1:
        raise Retry(defer=0)
    return {'value': value, 'attempt': ctx['job_try']}


async def main():
    if os.environ.get('ENVIRONMENT') not in {'staging', 'test'}:
        raise RuntimeError('Set ENVIRONMENT=staging or test; production probes are refused')
    url = os.environ['REDIS_URL']
    parsed = urlsplit(url)
    if parsed.hostname not in {'localhost', '127.0.0.1'} and parsed.scheme != 'rediss':
        raise RuntimeError('Remote Redis probe requires TLS')
    queue = f'atlasops:pilot-probe:{uuid4().hex}'
    connection = RedisSettings.from_dsn(url)
    redis = await create_pool(connection)
    worker = None
    try:
        job = await redis.enqueue_job('pilot_probe', 'synthetic-probe', _queue_name=queue)
        assert job is not None
        worker = Worker(functions=[pilot_probe], redis_settings=connection, queue_name=queue,
                        burst=True, max_burst_jobs=3, max_jobs=1, max_tries=2,
                        poll_delay=0.1, job_timeout=10, keep_result=60)
        await asyncio.wait_for(worker.async_run(), timeout=30)
        result = await job.result(timeout=5)
        assert result == {'value': 'synthetic-probe', 'attempt': 2}
        print('PASS: Redis TCP enqueue, ARQ retry, execution and result retrieval')
    finally:
        if worker is not None:
            await worker.close()
        await redis.aclose(close_connection_pool=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        # Never echo connection strings/provider exceptions into deployment logs.
        print(f'FAIL: queue probe ({type(exc).__name__}); inspect provider access privately')
        raise SystemExit(1) from None
