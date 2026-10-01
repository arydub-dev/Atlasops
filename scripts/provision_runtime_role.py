"""Run with the backend Python environment after Alembic migrations.

Reads MIGRATION_DATABASE_URL, RUNTIME_DATABASE_ROLE, RUNTIME_DATABASE_PASSWORD.
Only use a dedicated runtime role. Does not print connection strings/passwords.
"""
import os
import psycopg
from psycopg import sql


def main():
    url = os.environ['MIGRATION_DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
    role = os.environ.get('RUNTIME_DATABASE_ROLE', 'atlasops_app')
    password = os.environ['RUNTIME_DATABASE_PASSWORD']
    if len(password) < 32:
        raise ValueError('Use a generated password of at least 32 characters')
    with psycopg.connect(url) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s', (role,))
            existing = cursor.fetchone()
            if existing and any(existing):
                raise ValueError('Refusing to use a privileged role as runtime')
            if not existing:
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role), sql.Literal(password)))
            cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}').format(sql.Identifier(role)))
            cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {}').format(sql.Identifier(role)))
    print('Runtime role grants configured; existing passwords were not changed.')


if __name__ == '__main__':
    main()
