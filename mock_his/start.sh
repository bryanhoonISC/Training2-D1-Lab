#!/bin/sh
# Starts the SFTP server, then the HL7 mock.
set -e
sh /app/sftp_seed.sh
/usr/sbin/sshd
exec python -u /app/his.py
