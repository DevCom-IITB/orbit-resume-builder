# Resume Renderer

Minimal Django service that renders structured resume data into PDF using LaTeX.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 manage.py migrate
python3 manage.py runserver
```

## Test

```bash
pytest
```

## API

POST `/api/resume-renderer/render/`

```json
{
  "header": {
    "name": "Jane Doe",
    "edu": "B.Tech",
    "contact": {
      "email": "jane@example.com",
      "phone": "+1 555 000",
      "linkedin": "jane-doe",
      "github": "janedoe"
    }
  },
  "education": [],
  "experience": [],
  "key_projects": [],
  "config": {
    "compact": false,
    "header_style": "short",
    "use_header": true
  }
}
```

Response: PDF bytes.
