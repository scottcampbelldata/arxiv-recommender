#!/usr/bin/env bash
# Bootstrap the arxiv_recs database, arxrec_app role, schemas, and grants on
# the VPS. Idempotent. Runs against a local PostgreSQL 17 cluster.
#
# Usage:
#   sudo -u postgres bash setup-database.sh

set -euo pipefail

DB="${ARXREC_DB:-arxiv_recs}"
ROLE="${ARXREC_ROLE:-arxrec_app}"
SCHEMA_FILE="${SCHEMA_FILE:-$(dirname "$0")/../arxrec/db/schema.sql}"
APP_PW="${ARXREC_APP_PW:-}"

if [ -z "$APP_PW" ]; then
    APP_PW=$(openssl rand -base64 24 | tr '+/' '-_' | tr -d '=')
    echo ">> generated app password: $APP_PW"
fi

echo ">> creating role $ROLE if missing"
psql -v ON_ERROR_STOP=1 -d postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='$ROLE') THEN
    CREATE ROLE $ROLE LOGIN PASSWORD '$APP_PW';
  ELSE
    ALTER ROLE $ROLE WITH LOGIN PASSWORD '$APP_PW';
  END IF;
END \$\$;
SQL

if ! psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB'" | grep -q 1; then
    echo ">> creating database $DB owned by $ROLE"
    psql -v ON_ERROR_STOP=1 -d postgres -c "CREATE DATABASE $DB OWNER $ROLE;"
fi

echo ">> enabling pg_trgm"
psql -v ON_ERROR_STOP=1 -d "$DB" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo ">> applying schema"
psql -v ON_ERROR_STOP=1 -d "$DB" -f "$SCHEMA_FILE"

echo ">> granting schema privileges to $ROLE"
psql -v ON_ERROR_STOP=1 -d "$DB" <<SQL
GRANT USAGE, CREATE ON SCHEMA core, ml, ops TO $ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA core, ml, ops TO $ROLE;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA core, ml, ops TO $ROLE;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, ml, ops GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLES TO $ROLE;
ALTER DEFAULT PRIVILEGES IN SCHEMA core, ml, ops GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO $ROLE;
SQL

echo ""
echo ">> done. Add the following to platform/.env on the VPS:"
echo "PGHOST=localhost"
echo "PGPORT=5432"
echo "PGDATABASE=$DB"
echo "PGUSER=$ROLE"
echo "PGPASSWORD=$APP_PW"
