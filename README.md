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

## Note to contributors
- Please run `ruff . --fix` in the `server` directory before committing to ensure code quality and consistency.
- Please run `pytest` in the `server` directory to ensure all tests pass before pushing your changes.
- Please run `npm test` in the `client` directory to ensure all frontend tests pass before pushing your changes.
- Please lint your JavaScript code using `eslint` in the `client` directory and checking with `npm run lint` before committing to maintain code quality and consistency.
- Please ensure that any new features or bug fixes are accompanied by appropriate tests to maintain the integrity of the codebase.

## Taskfile

A `Taskfile.yml` is included in the project to automate common tasks such as setting up the development environment, running tests, and starting the development server. To use the Taskfile, you can run commands like: