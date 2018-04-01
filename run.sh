#!/bin/sh
export GOOGLE_APPLICATION_CREDENTIALS=vidsearch_service_account.json
export FLASK_APP=server.py
flask run

