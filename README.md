# AI-Powered Quiz Generator from Documents

Engineering's Thesis Project - Adam Orłowski, 2025

Engineering's Thesis Supervisor - dr inż. Tomasz Walkowiak

## Project Description

A web application that supports learning by generating quizzes for uploaded text documents using a language model.

## Project Goal

The aim of this project was to design and develop a web application that enables users to learn by generating quizzes based on specific materials uploaded by them. The user uploads a text file, and a language model automatically generates questions and answers from its content, with one correct answer and the rest being incorrect. The application will present these in the form of an interactive quiz, where the user can select answers and immediately find out whether their choice was right or wrong.

## Features

### For Users:

- Registration and authentication (JWT)
- Upload PDF/TXT documents
- Automatic question generation by AI
- Edit generated quizzes
- Take quizzes with scoring system
- Favorite quizzes system
- Public and private quizzes

### For Administrators:

- Users and quizzes management

## Technologies

### Backend

- **FastAPI** - web framework
- **PostgreSQL** - database
- **SQLAlchemy** (async) - ORM
- **OpenAI API** - LLM integration (via Clarin.eu)
- **JWT** - authentication
- **Custom PDF Parser** - text extraction from PDFs

### Frontend

- **Vue 3** - JavaScript framework (Composition API)
- **Vue Router** - routing
- **Axios** - HTTP client
- **Tailwind CSS** - styling
- **Vite** - build tool

## Installation and Setup

### Requirements

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### 1. Database Configuration

```bash
# Create PostgreSQL database
createdb quiz_app
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv env
source env/bin/activate  # Linux/Mac
# or: env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy the .env.example file to .env and set your environment variables
cp .env.example .env

# Run migrations
alembic upgrade head

# Create admin account
python -m app.scripts.add_admin

# Start development server
uvicorn app.main:app --reload
```

Backend available at: `http://localhost:7000`  
API Documentation (Swagger): `http://localhost:7000/docs`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend available at: `http://localhost:3000`

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │ ◄─────► │   FastAPI    │ ◄─────► │ PostgreSQL  │
│   (Vue 3)   │  HTTP   │   Backend    │   SQL   │   Database  │
└─────────────┘         └──────────────┘         └─────────────┘
                               │
                               │ HTTP
                               ▼
                        ┌──────────────┐
                        │ Clarin LLM   │
                        │   (GPT-4o)   │
                        └──────────────┘
```

### Quiz Generation Flow:

1. User uploads PDF/TXT file
2. Backend extracts text from document
3. Text is split into chunks
4. Each chunk is sent to LLM with prompt
5. LLM generates questions in JSON format
6. Backend validates and saves questions to database
7. Frontend displays ready quiz

## Project Structure

```
web_app/
├── backend/
│   ├── app/
│   │   ├── exceptions/       # Custom exceptions
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── pdf_parser/       # PDF parser
│   │   ├── routers/          # API endpoints
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── scripts/          # Utility scripts
│   │   ├── services/         # Business logic
│   │   ├── settings/         # Database and environmental variables settings
│   │   ├── main.py           # Entry point
│   │   ├── oauth2.py         # Authentication methods
│   │   ├── utils.py          # Small utils methods
│   │   └── ...
│   ├── alembic/              # Database migrations
│   ├── alembic.ini           # Alembic inicialization file
│   ├── .env.example          # Environmental variables
│   └── requirements.txt
│
│── frontend/
│   ├── src/
│   │   ├── assets/           # Assets
│   │   ├── components/       # Vue components
│   │   ├── router/           # Routing configuration
│   │   ├── services/         # API client
│   │   ├── views/            # Page views
│   │   └── App.vue
│   │   └── main.js
│   │── package.json
│   └── ...
└── ...
```

## Security

- Passwords hashed with bcrypt algorithm
- JWT token-based authentication
- CORS configured for secure communication
- Backend data validation (Pydantic)
- Permission checks at endpoint level

## License

Project created for Engineering's thesis purposes.

## Author

Adam Orłowski  
Wrocław University of Science and Technology, 2025

---

## Additional Information

### LLM Configuration

The application uses Clarin.eu API to access the GPT-4o model.
API key can be obtained after registration at https://services.clarin-pl.eu/

### Limits

- Supported formats: PDF, TXT

### Known Issues

- PDF parser may have difficulties with files containing complex formatting and complicated fonts
- Generating quizzes from long documents will take longer time
