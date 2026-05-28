#!/bin/bash

RDS_HOST="chatapp-db01.cluster-cknio6ek2ah3.us-east-1.rds.amazonaws.com"

kubectl run db-init \
  --image=python:3.11-slim \
  --restart=Never \
  --attach=true \
  --stdin=true \
  --rm=true \
  -n chatapp \
  --command -- bash -c "
python3 -u - << 'EOF'
import subprocess, sys, urllib.request

print('Installing dependencies...', flush=True)

subprocess.check_call([
    sys.executable,
    '-m',
    'pip',
    'install',
    'pymysql',
    'cryptography',
    '--quiet'
])

print('Dependencies installed', flush=True)

import pymysql

print('Downloading RDS CA bundle...', flush=True)

urllib.request.urlretrieve(
    'https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem',
    '/tmp/global-bundle.pem'
)

print('Connecting to MySQL...', flush=True)

conn = pymysql.connect(
    host='${RDS_HOST}',
    port=3306,
    user='admin',
    passwd='password01',
    ssl_ca='/tmp/global-bundle.pem',
    ssl_verify_cert=True,
    connect_timeout=10,
)

print('Connected successfully', flush=True)

cur = conn.cursor()

print('Creating database...', flush=True)

cur.execute('''
CREATE DATABASE IF NOT EXISTS chatdb
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci
''')

conn.commit()

print('Listing databases...', flush=True)

cur.execute('SHOW DATABASES')

dbs = [r[0] for r in cur.fetchall()]

conn.close()

print(f'Done. Databases: {\", \".join(dbs)}', flush=True)
EOF
"
