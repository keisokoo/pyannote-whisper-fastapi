#!/bin/bash

git pull origin master && sudo systemctl restart fastapi && sudo systemctl restart celery