#! /bin/sh
venv/bin/pip install -U -r requirements.txt
rm -rf ./prommetrics; mkdir ./prommetrics
venv/bin/uvicorn api:app --workers 2 --port 5000 --proxy-headers
