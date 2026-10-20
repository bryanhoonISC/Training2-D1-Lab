#!/bin/sh
# Puts the test files of Part G in /home/his/outbox. Run it again to get the files back:
#   docker compose exec mock_his sh /app/sftp_seed.sh
set -e
dir=/home/his/outbox
rm -rf "$dir"
mkdir -p "$dir"
cd "$dir"
for f in claim_HN00012345.pdf labresult_HN00012345.txt PAT-01_HN00012345.hl7; do
  echo "Test file. Not processed." > "$f"
  touch -d "10 days ago" "$f"
done
for f in claim_HN00067890.pdf labresult_HN00067890.txt; do
  echo "Test file. Waiting to be processed." > "$f"
done
chown -R his:his "$dir"
echo "sftp seed: $(ls | wc -l) files in $dir"
