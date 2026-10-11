"""Actual sync_connection/ARQ subprocess recovery with synthetic Salesforce HTTP.

Only the remote HTTP boundary is replaced; real Redis AOF, worker processes,
application job state, connector mapping and database transactions are exercised.
"""
import asyncio
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

import pytest
from sqlalchemy import select
from app.core.database import engine
from app.connectors.credentials import encrypt_credentials
from app.models import Connection, ImportJob, Supplier
from app.models.enums import ConnectorType, ConnectorStatus
from app.tenancy.rls import set_session_org

pytestmark=pytest.mark.skipif(os.environ.get('SUPPLY_CI_POSTGRES')!='1' or not os.environ.get('ATLAS_QA_RUN'),
    reason='Worker faults require disposable QA PostgreSQL and privately owned Redis')

CHILD=r'''
import sys, time, asyncio
from pathlib import Path
import httpx
from arq.worker import Worker
from arq.connections import RedisSettings
from app.connectors.jobs import sync_connection
url, mode, marker = sys.argv[1:]
def handler(request):
    if '/query' in str(request.url):
        if mode=='hold':
            Path(marker).write_text('executing')
            while True: time.sleep(.05)
        if mode=='db_loss' and not Path(marker).exists():
            Path(marker).write_text('executing')
            while not Path(marker+'.release').exists(): time.sleep(.05)
        if mode=='fail': raise httpx.ConnectError('Synthetic upstream connection unavailable',request=request)
        return httpx.Response(200,json={'done':True,'records':[{'Id':'RECOVERY-ACCOUNT','Name':'Synthetic recovery supplier','BillingCountry':'US','Type':'Vendor','SystemModstamp':'2026-03-01T00:00:00.000+0000'}]})
    return httpx.Response(200,json={'access_token':'synthetic','instance_url':'https://acme.my.salesforce.com'})
original=httpx.AsyncClient
def client(*args,**kwargs):
    kwargs['transport']=httpx.MockTransport(handler)
    return original(*args,**kwargs)
httpx.AsyncClient=client
Worker(functions=[sync_connection],redis_settings=RedisSettings.from_dsn(url),
       job_timeout=2, max_tries=5, retry_jobs=True, poll_delay=.1, health_check_interval=1).run()
'''


@pytest.fixture
def isolated_redis(tmp_path):
    binary=shutil.which('redis-server')
    assert binary, 'redis-server required for fault evidence'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    url=f'redis://127.0.0.1:{port}/0'
    processes=[]; log=(tmp_path/'redis.log').open('w')
    def start():
        proc=subprocess.Popen([binary,'--bind','127.0.0.1','--port',str(port),'--save','',
            '--appendonly','yes','--appendfsync','always','--dir',str(tmp_path)],stdout=log,stderr=subprocess.STDOUT)
        processes.append(proc)
        from redis import Redis
        client=Redis.from_url(url,socket_connect_timeout=.2,socket_timeout=.2)
        for _ in range(100):
            try:
                if client.ping(): client.close(); return proc
            except Exception: time.sleep(.05)
        raise AssertionError('Owned Redis did not start')
    proc=start()
    try: yield url,proc,start
    finally:
        for proc in processes:
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=10)
        log.close()


def setup_connection(db,org):
    assert (Path(os.environ['ATLAS_QA_RUN'])/'SYNTHETIC_ONLY').exists()
    assert engine.url.host=='127.0.0.1' and engine.url.username=='qa_app'
    set_session_org(db,org.id)
    conn=Connection(organization_id=org.id,name='Fault recovery',connector_type=ConnectorType.SALESFORCE,
        status=ConnectorStatus.CONNECTED,config={'http_retries':0},
        credentials_encrypted=encrypt_credentials({'client_id':'synthetic','client_secret':'synthetic'}),is_active=True)
    db.add(conn);db.commit();return conn.id


def start_worker(tmp_path,url,mode):
    log=(tmp_path/(mode+'.log')).open('w')
    proc=subprocess.Popen([sys.executable,'-c',CHILD,url,mode,str(tmp_path/'checkpoint')],
        env={**os.environ, 'PGAPPNAME':'qa-fault-'+tmp_path.name},stdout=log,stderr=subprocess.STDOUT)
    return proc,log


def stop(proc,log):
    if proc.poll() is None: proc.kill();proc.wait(timeout=10)
    log.close()


async def queue(url,conn,org,job_id):
    from arq.connections import create_pool, RedisSettings
    pool=await create_pool(RedisSettings.from_dsn(url))
    try:
        return await pool.enqueue_job('sync_connection',str(conn),str(org),'incremental',_job_id=job_id)
    finally: await pool.aclose()


async def outcome(url,job_id):
    from arq.connections import create_pool, RedisSettings
    from arq.jobs import Job
    pool=await create_pool(RedisSettings.from_dsn(url))
    try: return await Job(job_id,pool).result(timeout=55,poll_delay=.1)
    finally: await pool.aclose()


def test_worker_kill_redis_restore_duplicate_and_restart(db,org_a,tmp_path,isolated_redis):
    url,redis_proc,restart=isolated_redis
    org=org_a[0]; oid=org.id; cid=setup_connection(db,org); jid='fault-'+uuid4().hex
    assert asyncio.run(queue(url,cid,oid,jid)) is not None
    assert asyncio.run(queue(url,cid,oid,jid)) is None
    # A queued job must survive a real Redis restart before any worker starts.
    redis_proc.terminate();redis_proc.wait(timeout=10)
    redis_proc=restart()
    worker,log=start_worker(tmp_path,url,'hold')
    try:
        deadline=time.monotonic()+20
        while not (tmp_path/'checkpoint').exists() and worker.poll() is None and time.monotonic()<deadline: time.sleep(.05)
        assert (tmp_path/'checkpoint').exists(), 'Actual connector execution checkpoint missing'
        set_session_org(db,oid);db.expire_all()
        jobs=db.scalars(select(ImportJob).where(ImportJob.organization_id==oid)).all()
        assert len(jobs)==1 and jobs[0].status.value=='running'
        db.commit()
        stop(worker,log)
        redis_proc.terminate();redis_proc.wait(timeout=10)
        from redis import Redis
        client=Redis.from_url(url,socket_connect_timeout=.2,socket_timeout=.2)
        try:
            with pytest.raises(Exception): client.ping()
        finally: client.close()
        restart()  # Existing AOF, no flush or queue reconstruction.
        worker,log=start_worker(tmp_path,url,'normal')
        result=asyncio.run(outcome(url,jid))
        assert result['status']=='success' and result['records_imported']==1
        assert asyncio.run(queue(url,cid,oid,jid)) is None
        db.expire_all();set_session_org(db,oid)
        jobs=db.scalars(select(ImportJob).where(ImportJob.organization_id==oid)).all()
        assert len(jobs)==1 and jobs[0].status.value=='success'
        assert jobs[0].mapping['job_try']==2
        suppliers=db.scalars(select(Supplier).where(Supplier.organization_id==oid)).all()
        assert len(suppliers)==1 and suppliers[0].external_id=='RECOVERY-ACCOUNT'
        db.commit()
        # Redeliver the same business operation with a fresh queue identity.
        replay=jid+'-redelivery'
        assert asyncio.run(queue(url,cid,oid,replay)) is not None
        assert asyncio.run(outcome(url,replay))['status']=='success'
        db.expire_all();set_session_org(db,oid)
        assert len(db.scalars(select(Supplier).where(Supplier.organization_id==oid)).all())==1
        assert len(db.scalars(select(ImportJob).where(ImportJob.organization_id==oid)).all())==2
    finally: stop(worker,log)


def test_worker_bounded_retries_report_terminal_failure(db,org_a,tmp_path,isolated_redis):
    url,_,_=isolated_redis
    org=org_a[0]; oid=org.id;cid=setup_connection(db,org);jid='fault-'+uuid4().hex
    asyncio.run(queue(url,cid,oid,jid))
    worker,log=start_worker(tmp_path,url,'fail')
    try:
        with pytest.raises(Exception): asyncio.run(outcome(url,jid))
        db.expire_all();set_session_org(db,oid)
        jobs=db.scalars(select(ImportJob).where(ImportJob.organization_id==oid)).all()
        assert len(jobs)==1 and jobs[0].status.value=='failed'
        assert jobs[0].mapping['retry_count']==5 and jobs[0].mapping['phase']=='failed'
        assert jobs[0].error_summary
        assert db.get(Connection,cid).status.value=='error'
        assert db.scalars(select(Supplier).where(Supplier.organization_id==oid)).all()==[]
    finally: stop(worker,log)


def test_worker_database_connection_loss_recovers(db,org_a,tmp_path,isolated_redis):
    from sqlalchemy import text
    url,_,_=isolated_redis
    org=org_a[0];oid=org.id;cid=setup_connection(db,org);jid='fault-'+uuid4().hex
    asyncio.run(queue(url,cid,oid,jid))
    worker,log=start_worker(tmp_path,url,'db_loss')
    try:
        deadline=time.monotonic()+20
        while not (tmp_path/'checkpoint').exists() and worker.poll() is None and time.monotonic()<deadline: time.sleep(.05)
        assert (tmp_path/'checkpoint').exists()
        pids=db.execute(text("SELECT pid FROM pg_stat_activity WHERE application_name=:name"),
                        {'name':'qa-fault-'+tmp_path.name}).scalars().all()
        assert pids, 'No actual worker database connection found'
        for pid in pids:
            assert db.execute(text('SELECT pg_terminate_backend(:pid)'),{'pid':pid}).scalar() is True
        db.commit()
        (tmp_path/'checkpoint.release').write_text('resume')
        result=asyncio.run(outcome(url,jid))
        assert result['status']=='success'
        db.expire_all();set_session_org(db,oid)
        jobs=db.scalars(select(ImportJob).where(ImportJob.organization_id==oid)).all()
        assert len(jobs)==1 and jobs[0].status.value=='success'
        assert jobs[0].mapping['job_try']==2
        assert len(db.scalars(select(Supplier).where(Supplier.organization_id==oid)).all())==1
    finally: stop(worker,log)
