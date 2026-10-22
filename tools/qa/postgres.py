"""Optional disposable PostgreSQL migration/RLS verification; no supplied DB URLs."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time


def verify(root,run,env,python):
    import psycopg
    initdb=shutil.which('initdb');postgres=shutil.which('postgres')
    if not initdb or not postgres or (hasattr(os,'geteuid') and os.geteuid()==0):
        return False,'Local initdb/postgres under an unprivileged user is required'
    folder=run/'postgres';folder.mkdir(mode=0o700)
    data=folder/'data'
    with (run/'postgres.log').open('w') as log:
        init=subprocess.run([initdb,'-D',str(data),'-U','qa_owner','--auth=trust','--no-locale','--encoding=UTF8'],env=env,stdout=log,stderr=subprocess.STDOUT)
        if init.returncode:return False,'PostgreSQL initialization failed; postgres.log'
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        # Disable Unix sockets (path length limits) and accept only loopback connections.
        proc=subprocess.Popen([postgres,'-D',str(data),'-h','127.0.0.1','-p',str(port),'-k',''],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            owner=f'postgresql://qa_owner@127.0.0.1:{port}/postgres'
            for _ in range(100):
                try:
                    with psycopg.connect(owner,connect_timeout=1):break
                except psycopg.OperationalError:time.sleep(.1)
            else:return False,'PostgreSQL startup failed; postgres.log'
            migration=folder/'alembic.ini'
            migration.write_text((root/'backend/alembic.ini').read_text().replace('script_location = alembic','script_location = '+str(root/'backend/alembic')))
            pg_env={**env,'DATABASE_URL':owner.replace('postgresql://','postgresql+psycopg://'),'SUPPLY_CI_POSTGRES':'1'}
            code=subprocess.run([python,'-m','alembic','-c',str(migration),'upgrade','head'],cwd=folder,env=pg_env,stdout=log,stderr=subprocess.STDOUT).returncode
            if code:return False,'Alembic migration failed; postgres.log'
            with psycopg.connect(owner,autocommit=True) as db:
                db.execute('CREATE ROLE qa_app LOGIN NOSUPERUSER NOBYPASSRLS')
                db.execute('GRANT USAGE ON SCHEMA public TO qa_app')
                db.execute('GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public TO qa_app')
                db.execute('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO qa_app')
                role=db.execute("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname='qa_app'").fetchone()
                assert role==(False,False)
            pg_env['DATABASE_URL']=f'postgresql+psycopg://qa_app@127.0.0.1:{port}/postgres'
            with (run/'postgres-tests.log').open('w') as output:
                code=subprocess.run([python,'-m','pytest',str(root/'backend/tests'),'-q','--junitxml='+str(run/'postgres.xml')],cwd=folder,env=pg_env,stdout=output,stderr=subprocess.STDOUT,timeout=600).returncode
            return code==0,f'Migrated fresh PostgreSQL, verified NOSUPERUSER/NOBYPASSRLS application role; pytest exit {code}'
        finally:
            proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
