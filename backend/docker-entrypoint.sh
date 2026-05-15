#!/usr/bin/env bash
set -e

# Wait for Postgres to be ready using Python
echo "Waiting for postgres at $POSTGRES_HOST:$POSTGRES_PORT..."
python -c "
import socket
import time
import sys

max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('$POSTGRES_HOST', int('$POSTGRES_PORT')))
        sock.close()
        
        if result == 0:
            print(f'✓ Postgres is ready!')
            sys.exit(0)
    except Exception as e:
        pass
    
    retry_count += 1
    print(f'Waiting... ({retry_count}/{max_retries})')
    time.sleep(1)

print('✗ Postgres failed to be ready')
sys.exit(1)
"

# Run migrations
echo "Running alembic migrations..."
alembic upgrade head || true

# Start the server
echo "Starting application..."
exec "$@"
