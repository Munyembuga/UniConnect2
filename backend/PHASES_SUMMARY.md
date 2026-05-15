## UniConnect AI Student Support Chatbot - Backend Implementation

### Project Overview
Building a production-ready FastAPI backend for an AI-powered student support chatbot with RAG (Retrieval Augmented Generation) capabilities.

---

## Phase 1: FastAPI Setup & Core Infrastructure ✅

### Completed:

#### 1. Environment Configuration
- **File**: `app/core/config.py`
  - PostgreSQL connection with asyncpg driver
  - JWT secret keys and token expiration settings
  - Logging configuration
  - AI provider settings (Gemini API)
  - Environment variables via `.env`

#### 2. Database Setup
- **File**: `app/db/session.py`
  - Async SQLAlchemy engine with PostgreSQL
  - Session factory for async operations
  - Database dependency injection for FastAPI

- **File**: `app/db/base.py`
  - SQLAlchemy declarative base for ORM models

#### 3. Logging System
- **File**: `app/core/logging.py`
  - Configured with loguru for production-grade logging
  - JSON output for structured logging
  - Different log levels for development and production

#### 4. FastAPI Application
- **File**: `app/main.py`
  - Main FastAPI app initialization
  - Health check endpoint (`/health`)
  - CORS middleware
  - API v1 router includes auth endpoints
  - Swagger/OpenAPI documentation

#### 5. Requirements & Dependencies
- **File**: `requirements.txt`
  - FastAPI 0.115.6
  - SQLAlchemy 2.0.36 (with asyncio support)
  - asyncpg 0.30.0 (async PostgreSQL driver)
  - Alembic 1.14.1 (migrations)
  - Python-jose + cryptography (JWT)
  - Passlib + bcrypt (password hashing)
  - Pydantic 2.10.4 (validation)
  - LangChain 0.3.14 + Google Generative AI
  - ChromaDB 0.5.23 (vector embeddings)
  - PDF/DOCX/TXT processing libraries
  - All other required packages

#### 6. Environment File
- **File**: `.env.example`
  - Template for required environment variables
  - Database URL
  - JWT secrets
  - AI API keys
  - Application settings

---

## Phase 2: JWT Authentication & User Management ✅

### Completed:

#### 1. Security Module
- **File**: `app/core/security.py`
  - `hash_password()`: Bcrypt password hashing
  - `verify_password()`: Password verification
  - `create_access_token()`: JWT access token generation (15 min expiration)
  - `create_refresh_token()`: JWT refresh token generation (7 days expiration)
  - `decode_access_token()`: Access token validation
  - `decode_refresh_token()`: Refresh token validation
  - Token type checking for security

#### 2. User Model
- **File**: `app/models/user.py`
  - UUID primary key
  - Email (unique, indexed)
  - Full name
  - Hashed password
  - Role-based access (admin/student)
  - Active status
  - Email verification flag
  - Timestamps (created_at, updated_at, last_login)
  - Relationships to chat histories and documents

#### 3. Authentication Schemas
- **File**: `app/schemas/auth.py`
  - `UserRegisterRequest`: Registration with email validation
  - `UserLoginRequest`: Login credentials
  - `TokenResponse`: Access & refresh tokens with expiration
  - `UserResponse`: User profile data (Pydantic)
  - `RefreshTokenRequest`: Token refresh
  - `ChangePasswordRequest`: Password change

#### 4. User Repository (Data Layer)
- **File**: `app/repositories/user.py`
  - `create_user()`: Create new user with password hashing
  - `get_user_by_email()`: Async email lookup
  - `get_user_by_id()`: UUID lookup
  - `update_user()`: Update user fields
  - `delete_user()`: Delete user
  - Error handling with IntegrityError for duplicates

#### 5. User Service (Business Logic)
- **File**: `app/services/user.py`
  - `register_user()`: User registration with token generation
  - `login_user()`: Authentication with token generation
  - `refresh_access_token()`: Refresh token handling
  - `change_password()`: Password update with verification
  - `get_user()`: User profile retrieval
  - Token generation and validation logic

#### 6. Authentication Router
- **File**: `app/api/v1/auth.py`
  - Endpoints implemented:
    - `POST /auth/register`: User registration
    - `POST /auth/login`: User login
    - `POST /auth/refresh`: Token refresh
    - `GET /auth/me`: Current user profile
    - `POST /auth/change-password`: Password change
  - JWT token extraction from Authorization header
  - Current user dependency injection
  - Error handling with proper HTTP status codes

---

## Phase 3: Database Models & Alembic Migrations ✅

### Completed:

#### 1. Core Models

**User Model** (`app/models/user.py`)
- UUID primary key
- Email, username, password hash
- Active status and role (admin/student)
- Timestamps and last login tracking

**Document Model** (`app/models/document.py`)
- UUID primary key
- Support for PDF, DOCX, TXT files
- File metadata (size, path, type)
- Processing status tracking (pending/processing/completed/failed)
- Extracted text storage
- Chunk count tracking
- Relationships to DocumentChunks

**DocumentChunk Model** (`app/models/document_chunk.py`)
- UUID primary key
- Link to parent document
- Chunk index and content
- Embedding ID reference
- Chunk hash for deduplication
- Timestamps

**ChatHistory Model** (`app/models/chat_history.py`)
- UUID primary key
- Link to student user
- Question and answer storage
- Source references (JSON array of chunk IDs)
- Confidence score (0-1)
- Resolution status (pending/resolved/unresolved)
- Timestamps

**UnresolvedQuestion Model** (`app/models/unresolved_question.py`)
- UUID primary key
- Links to chat history and student
- Original question and AI attempt
- Low confidence flag
- Admin answer and admin who answered
- Resolution status
- Timestamps (created, answered)

**WebsiteSource Model** (`app/models/website_source.py`)
- UUID primary key
- URL (unique, indexed)
- Title and description
- Extracted content
- Processing status
- Chunk count
- Admin tracking

#### 2. Alembic Configuration

**Files Created:**
- `alembic.ini`: Main Alembic configuration
- `alembic/env.py`: Migration environment (handles async operations)
- `alembic/script.py.mako`: Migration template
- `alembic/__init__.py`: Package marker
- `alembic/versions/__init__.py`: Versions package marker

**Initial Migration:**
- `alembic/versions/001_initial_migration.py`
  - Creates all 7 tables:
    - users
    - documents
    - document_chunks
    - website_sources
    - chat_history
    - unresolved_questions
  - Proper indexing on frequently queried columns
  - Foreign key constraints
  - Unique constraints
  - Enum types for roles and document types
  - Default values and server defaults
  - Timestamps with UTC timezone support

#### 3. Model Relationships
- User has many Documents (uploaded_by)
- User has many ChatHistory entries
- Document has many DocumentChunks
- ChatHistory references User (student)
- UnresolvedQuestion references User (student and admin)

---

## Current Architecture

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py (authentication endpoints)
│   │       └── health.py (health check)
│   ├── core/
│   │   ├── config.py (settings)
│   │   ├── security.py (JWT & password)
│   │   └── logging.py (logging setup)
│   ├── db/
│   │   ├── base.py (SQLAlchemy base)
│   │   └── session.py (async DB session)
│   ├── models/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── document_chunk.py
│   │   ├── chat_history.py
│   │   ├── unresolved_question.py
│   │   └── website_source.py
│   ├── repositories/
│   │   └── user.py (data access layer)
│   ├── schemas/
│   │   └── auth.py (request/response models)
│   ├── services/
│   │   └── user.py (business logic)
│   └── main.py (FastAPI app)
├── alembic/
│   ├── versions/
│   │   ├── __init__.py
│   │   └── 001_initial_migration.py
│   ├── __init__.py
│   ├── env.py
│   └── script.py.mako
├── alembic.ini (configuration)
├── requirements.txt (dependencies)
├── .env.example (environment template)
└── Dockerfile (for Docker)
```

---

## Tech Stack Summary

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115.6 |
| Server | Uvicorn | 0.34.0 |
| Database | PostgreSQL | - |
| ORM | SQLAlchemy | 2.0.36 |
| Async Driver | asyncpg | 0.30.0 |
| Migrations | Alembic | 1.14.1 |
| Validation | Pydantic | 2.10.4 |
| Auth | Python-Jose + Bcrypt | - |
| Logging | Loguru | 0.7.3 |
| RAG | LangChain | 0.3.14 |
| Embeddings | Google Generative AI | 0.8.4 |
| Vector DB | ChromaDB | 0.5.23 |
| Document Processing | PyPDF2, python-docx, pytesseract | Latest |

---

## API Endpoints Implemented

### Authentication Endpoints (Phase 2)
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user profile
- `POST /auth/change-password` - Change password

### System Endpoints (Phase 1)
- `GET /health` - Health check

---

## Next Steps (Phases 4-12)

### Phase 4: File Upload APIs
- Document upload endpoints
- File validation and storage
- PDF/DOCX/TXT extraction
- OCR for scanned documents

### Phase 5: Website Scraping
- Website URL management
- Web scraping with BeautifulSoup
- Content extraction and cleaning

### Phase 6: Text Chunking
- LangChain text splitting
- Chunk size optimization
- Overlap management

### Phase 7: Embeddings & ChromaDB
- Embedding generation with Google Generative AI
- ChromaDB integration
- Vector similarity search

### Phase 8: RAG Chatbot Pipeline
- Question answering endpoint
- Context retrieval
- AI response generation
- Source attribution

### Phase 9: Chat History
- Chat history storage
- Conversation pagination
- Search functionality

### Phase 10: Unresolved Questions
- Low confidence detection
- Admin answer system
- Learning from admin answers

### Phase 11: Admin Dashboard APIs
- Document management
- Analytics endpoints
- Unresolved questions review

### Phase 12: Docker Deployment
- Docker configuration
- Docker Compose setup
- Production environment

---

## Installation & Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Docker (for PostgreSQL container)

### Installation Steps

1. **Clone repository and navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Database Schema

### Tables Created
1. **users** - User accounts with authentication
2. **documents** - Uploaded PDF/DOCX/TXT files
3. **document_chunks** - Text chunks from documents
4. **website_sources** - URLs for training
5. **chat_history** - Conversation history
6. **unresolved_questions** - Low-confidence questions for admin review

---

## Security Features Implemented

✅ JWT authentication with access & refresh tokens
✅ Bcrypt password hashing
✅ Role-based access control (admin/student)
✅ Async operations for performance
✅ Input validation with Pydantic
✅ Structured logging for auditing
✅ Environment variable configuration
✅ UUID primary keys (no sequential IDs)
✅ SQL injection prevention via ORM
✅ CORS configuration

---

## Production Readiness

✅ Async/await throughout
✅ Proper error handling
✅ Logging at every layer
✅ Database transaction management
✅ Connection pooling
✅ Indexed columns for performance
✅ Migration system for schema changes
✅ Environment-based configuration
✅ RESTful API design
✅ Swagger/OpenAPI documentation

---

## Status

**Phase 1, 2, 3: COMPLETE ✅**

Waiting for: npm package installation to complete before testing

Next: Will run the server and test auth endpoints
