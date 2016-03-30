#/bin/bash
./scripts/echo_version_json.sh > ./embedly/version.json
docker build -t app:build embedly/
