#! /bin/sh

rm -rf ./prommetrics; mkdir ./prommetrics
venv/bin/uvicorn api:app --workers 2 --port 5000 --proxy-headers
