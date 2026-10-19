#!/bin/bash
# Runs under the -a hook of /iris-main, AFTER IRIS has started.
# Never call "iris start" here: it fails and takes the container down.
set -e

echo "[insurligent-setup] running first-start setup"
iris session IRIS -U %SYS < /opt/insurligent/setup/setup.script
echo "[insurligent-setup] hook finished"
