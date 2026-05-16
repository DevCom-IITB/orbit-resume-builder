# Resume Builder

Django + React app to generate PDF resumes from user input.

## Setup Backend

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

## Setup Frontend

```bash
cd client
npm install
npm start
```
