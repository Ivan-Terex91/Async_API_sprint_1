#!/bin/bash
set -e

psql -U $POSTGRES_USER -d $POSTGRES_DB -f /dumps/movies_db.sql
