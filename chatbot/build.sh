set -o errexit  # exit on error

pip install -r chatbot/requirements.txt

python chatbot/manage.py collectstatic --no-input

python chatbot/manage.py migrate
