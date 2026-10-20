# Test hospital system (HIS): the HL7 mock (his.py) and an SFTP server for Part G.
# SFTP login: his / his. The folder /home/his/outbox gets its test files at each start.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd \
 && ssh-keygen -A \
 && useradd -m his \
 && echo "his:his" | chpasswd
