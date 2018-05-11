#!/bin/bash

# Check if migration is needed.
python manage.py makemigrations --dry-run --noinput | grep -q "No changes detected"

if [ $? -ne 0 ]
then
    echo "Migrations up-to-date with models. Proceed with the deployment"
    exit 0
else
    echo "Migrations needed, setting Heroku app to maintenance mode."
    python ./ci/patch_heroku_app.py ${HEROKU_APP_NAME} ${HEROKU_API_KEY} maintenance true
    echo "Scaling down beat dynos to 0."
    python ./ci/patch_heroku_app.py ${HEROKU_APP_NAME}/formation/beat ${HEROKU_API_KEY} quantity 0
    echo "Running migrations."
    python manage.py migrate
    echo "Migrations done, switching maintenance mode off."
    python ./ci/patch_heroku_app.py ${HEROKU_APP_NAME} ${HEROKU_API_KEY} maintenance false
    echo "Scaling beat dynos up back to 1."
    python ./ci/patch_heroku_app.py ${HEROKU_APP_NAME}/formation/beat ${HEROKU_API_KEY} quantity 1
fi