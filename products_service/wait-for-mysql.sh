#!/bin/bash
# wait-for-mysql.sh

set -e

HOST="$1"
shift
CMD="$@"

echo "Waiting for MySQL at $HOST to be ready..."

# Wait until MySQL is ready
until mysql -h "$HOST" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1" &> /dev/null; do
  echo "MySQL is unavailable - sleeping 2s"
  sleep 2
done

echo "MySQL is up - executing command: $CMD"
exec $CMD
