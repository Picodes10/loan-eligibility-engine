#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE n8n;
    CREATE DATABASE loan_engine;
    GRANT ALL PRIVILEGES ON DATABASE n8n TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE loan_engine TO postgres;
EOSQL

echo "Databases created successfully!"