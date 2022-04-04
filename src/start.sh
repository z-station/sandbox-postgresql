#!/bin/bash
gunicorn --bind 0:9003 app.main:app --reload -w ${GUNICORN_WORKERS:=1}