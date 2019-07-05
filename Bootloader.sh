#! /bin/sh
venv/bin/uvicorn api:app --workers 2 --port 5000 --proxy-headers
