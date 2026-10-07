#!/usr/bin/env bash
set -u

cd /home/doshie/Doshie || exit 1

export HOME=/home/doshie
export PATH=/home/doshie/Doshie/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

exec 9>/tmp/doshie-supervisor.lock
flock -n 9 || exit 0

while true; do
    echo "$(date -Is) Starting Doshie" >> /home/doshie/Doshie/doshie-supervisor.log

    /home/doshie/Doshie/.venv/bin/python /home/doshie/Doshie/Doshie_web.py >> /home/doshie/Doshie/doshie-supervisor.log 2>&1

    code=$?

    echo "$(date -Is) Doshie exited with code $code; restarting in 5 seconds" >> /home/doshie/Doshie/doshie-supervisor.log

    sleep 5
done
