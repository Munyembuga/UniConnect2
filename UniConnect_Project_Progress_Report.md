# UniConnect — AI Student Support Chatbot
## Project Progress Report

**Student:** Munyembuga  
**Supervisor Presentation**  
**Date:** June 2026  
**Institution:** University of Rwanda

---

## 1. Project Overview

**UniConnect** is an AI-powered chatbot system designed to help University of Rwanda students get instant, accurate answers to their questions about university documents, procedures, admissions, scholarships, and academic programs.

Instead of waiting in queues or searching through long documents, students simply type or speak their question and the system finds and explains the relevant information from official university documents.

---

## 2. Problem Statement

University students face significant challenges accessing information:

- **Long queues** at administrative offices for simple procedural questions
- **Information scattered** across multiple PDFs, handbooks, and circulars
- **No 24/7 support** — offices are only open during working hours
- **Language barrier** — most documents are only in English, limiting access for some students
- **Unanswered questions** pile up with no tracking mechanism

UniConnect addresses all of these by combining document intelligence with an AI assistant.

---

## 3. System Architecture

```
┌────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                   │
│  Student Chat │ Admin Dashboard │ Document Management  │
└─────────────────────────┬──────────────────────────────┘
                          │  REST API  (HTTP/JSON)
┌─────────────────────────▼──────────────────────────────┐
│                  BACKEND (FastAPI / Python)             │
│                                                        │
│  Auth Service  │  Chat Service  │  Document Service    │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │           RAG PIPELINE (Knowledge Engine)        │  │
│  │                                                  │  │
│  │  Upload PDF/DOCX → Extract Text (OCR if needed) │  │
│  │  → Split into Chunks → Generate Embeddings      │  │
│  │  → Store in ChromaDB Vector Database            │  │
│  │                                                  │  │
│  │  Query → Embed → Vector Search + Keyword Search │  │
│  │  → RRF Merge → Gemini AI → Answer               │  │
│  └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
         │                    │                  │
    PostgreSQL            ChromaDB           Gemini API
    (Users, Chat,       (Vector Store)     (AI Generation
     Documents)                             + Embeddings)
```

---

## 4. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + Vite | User interface |
| **Styling** | Tailwind CSS | Responsive design |
| **Backend** | FastAPI (Python 3.11) | REST API |
| **Database** | PostgreSQL 16 | Users, chat history, documents |
| **Vector DB** | ChromaDB | Semantic search storage |
| **AI Generation** | Google Gemini 2.0 Flash | Answer generation |
| **AI Embeddings** | Gemini Embedding-001 | Text vectorization |
| **OCR Engine** | Tesseract 5.5 + pdf2image | Scanned document processing |
| **Containerization** | Docker + Docker Compose | Deployment |
| **Authentication** | JWT (Bearer tokens) | Secure access |

---

## 5. Key Features Implemented

### 5.1 Student-Facing Features

#### ✅ Intelligent Chat Interface
- Students type questions in natural language
- Voice input (microphone) supported — student speaks, text appears
- Text-to-speech — system reads answers aloud
- Bilingual support toggle (English / Kinyarwanda)
- Suggested questions to guide new users

#### ✅ Accurate Answer Generation (RAG Pipeline)
The system uses a **Retrieval-Augmented Generation (RAG)** pipeline:

1. The student's question is converted to a vector embedding
2. ChromaDB performs **semantic search** — finds relevant document sections by meaning, not just keywords
3. PostgreSQL performs **keyword search** — full-text search for exact terms
4. Both results are combined using **Reciprocal Rank Fusion (RRF)** — a proven algorithm that merges ranked lists
5. The top 5 most relevant passages are sent to Gemini AI with a strict prompt
6. Gemini generates a **reasoned, well-formatted answer** using only the document content

#### ✅ Answer Quality
- Answers are formatted with **bold**, bullet points, and numbered lists using Markdown rendering
- AI is instructed to **reason and synthesise** — not copy-paste document text
- Confidence scoring — if confidence is low, question is flagged for admin review
- Pre-answered questions from admins are matched first before running AI

### 5.2 Admin-Facing Features

#### ✅ Admin Dashboard
A full-featured admin portal with:

| Section | Functionality |
|---------|--------------|
| **Overview** | Live stats — queries today, answer rate, unresolved count |
| **Knowledge Base** | Upload, view, delete documents; see processing status |
| **Unanswered Queries** | Review low-confidence questions, provide manual answers |
| **Export Logs** | Full chat history with confidence scores, CSV export |
| **Analytics** | Query volume charts, category breakdown (mock data) |
| **FAQ Manager** | Create and manage curated Q&A pairs |

#### ✅ Document Upload Pipeline
1. Admin uploads a PDF, DOCX, or TXT file (up to 50 MB)
2. System automatically detects if the document is scanned or text-based
3. **Text-based PDF** → PyPDF2 extracts text instantly
4. **Scanned/image PDF** → Tesseract OCR reads the document (no API needed)
5. **Complex layouts** → Gemini Vision AI reads the pages as a fallback
6. Text is split into chunks → embedded → stored in ChromaDB
7. Document is available for student queries within minutes

#### ✅ Admin Answer Loop
When the AI cannot answer a question confidently:
1. Question is flagged as **unresolved** and appears in the admin dashboard
2. Admin reviews and types a correct answer
3. Next time any student asks a similar question → **admin answer is returned directly**, bypassing AI
4. This creates a self-improving knowledge base over time

### 5.3 Security & Authentication
- JWT-based authentication with access + refresh tokens
- Role-based access control: **Student** vs **Admin**
- Admin routes protected — redirect to login if unauthenticated
- Token stored in browser localStorage, sent as Bearer header

---

## 6. Document Processing — Scanned PDF Support

A key technical achievement is the three-tier OCR pipeline for scanned documents:

```
Upload PDF
    │
    ▼
[Tier 1] PyPDF2 — Extract embedded text
    │ if sparse/empty (scanned document)
    ▼
[Tier 2] Tesseract OCR — Local OCR engine
         • Converts PDF pages to 200 DPI images
         • Applies contrast enhancement + sharpening
         • Runs LSTM OCR engine (--oem 3)
         • No API calls — works offline, no rate limits
    │ if still poor quality
    ▼
[Tier 3] Gemini Vision — Cloud AI OCR
         • Sends page images to Gemini multimodal model
         • Retry logic with exponential backoff on rate limits
         • Tries multiple Gemini models as fallback
```

**Result:** Both digital and scanned PDFs are fully indexed and searchable.

---

## 7. System Flow — End to End

```
ADMIN SIDE                          STUDENT SIDE

1. Admin logs in                    1. Student registers / logs in
2. Admin uploads document           2. Student opens chat
3. System extracts text (OCR)       3. Student types question
4. Text chunked into 1000-char      4. System embeds question
   segments (200 overlap)           5. ChromaDB returns top 5 chunks
5. Chunks embedded with Gemini      6. PostgreSQL full-text search
6. Embeddings stored in ChromaDB    7. RRF merges both result sets
                                    8. Gemini generates answer
                                    9. Answer displayed with formatting
                                   10. If confidence < 40% → flagged
                                   
                                   ADMIN REVIEWS & ANSWERS
                                   → Next student gets admin answer
```

---

## 8. API Endpoints (Backend)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/auth/register` | Register new student | Public |
| POST | `/api/v1/auth/login` | Login, get JWT token | Public |
| POST | `/api/v1/chat/ask` | Ask a question | Student |
| GET | `/api/v1/chat/history` | My chat history | Student |
| POST | `/api/v1/documents/upload` | Upload document | Admin |
| GET | `/api/v1/documents` | List all documents | Admin |
| DELETE | `/api/v1/documents/{id}` | Delete document | Admin |
| GET | `/api/v1/admin/unresolved-questions` | View unanswered | Admin |
| POST | `/api/v1/admin/unresolved-questions/{id}/answer` | Answer question | Admin |
| GET | `/api/v1/admin/chat-history` | All chat logs | Admin |
| GET | `/api/v1/health` | System health check | Public |

Full interactive API documentation available at: **http://localhost:8000/docs**

---

## 9. How to Run the System

### Prerequisites
- Docker Desktop installed and running
- Node.js 18+ installed

### Start the Backend (Database + AI Services)
```bash
cd UniConnect
docker compose up -d
```
This starts:
- PostgreSQL database (port 5433)
- ChromaDB vector database (port 8001)
- FastAPI backend (port 8000)

### Start the Frontend (Student/Admin Interface)
```bash
cd UniConnect/frontend
npm install
npm run dev
```
Frontend available at: **http://localhost:5173**

### Default Admin Credentials
| Field | Value |
|-------|-------|
| Email | admin@uniconnect.com |
| Password | Admin@1234 |

---

## 10. Screenshots Description

### Student Chat Interface
- Clean, professional chat layout
- Voice recording button with live indicator
- Suggested questions shown on first load
- Bot answers rendered with proper formatting (bold, bullet lists, numbered steps)
- "Listen" button to hear answers read aloud
- Language toggle (EN / RW)

### Admin Dashboard
- Sidebar navigation with live unresolved question count badge
- Knowledge Base shows all uploaded documents with status (Indexed / Processing / Failed)
- Drag-and-drop style upload with progress percentage
- Unanswered Queries list with timestamp and AI confidence score
- Inline answer form — admin types answer, clicks Save & Mark Resolved
- Export Logs with CSV download button

---

## 11. Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Scanned PDFs have no extractable text | Three-tier OCR: PyPDF2 → Tesseract → Gemini Vision |
| Gemini API rate limits (429 errors) | Exponential backoff, model fallback chain, retry logic |
| AI copying document text verbatim | Rewrote prompt with explicit synthesis/reasoning instructions |
| CORS issues between frontend and backend | Vite proxy configuration forwards all `/api` calls to backend |
| Students asking general questions (greetings, date) | Pattern-matching detection bypasses RAG for conversational queries |
| Same question answered differently each time | Admin answer loop: once answered manually, all similar queries get same answer |
| Poor answer formatting in chat | Integrated `react-markdown` with custom styled components |

---

## 12. Current Status

| Component | Status |
|-----------|--------|
| Backend API | ✅ Complete |
| Database schema & migrations | ✅ Complete |
| RAG pipeline (vector + keyword + RRF) | ✅ Complete |
| PDF/DOCX/TXT text extraction | ✅ Complete |
| Scanned PDF OCR (Tesseract) | ✅ Complete |
| AI answer generation (Gemini) | ✅ Complete |
| Admin answer loop | ✅ Complete |
| Student chat interface | ✅ Complete |
| Voice input / text-to-speech | ✅ Complete |
| Admin dashboard | ✅ Complete |
| Document upload with progress | ✅ Complete |
| JWT authentication | ✅ Complete |
| Markdown formatting in chat | ✅ Complete |
| Docker containerization | ✅ Complete |

---

## 13. Planned Next Steps

- [ ] Kinyarwanda language support (translation layer)
- [ ] Email notifications for admin when unresolved queries exceed threshold
- [ ] Mobile application (React Native)
- [ ] Analytics dashboard with real-time data from backend
- [ ] Multi-institution support (multiple universities)
- [ ] Document re-indexing when content is updated
- [ ] Student satisfaction rating per answer

---

## 14. Technical Summary

UniConnect demonstrates practical application of:

- **Retrieval-Augmented Generation (RAG)** — grounding AI answers in real documents
- **Hybrid Search** — combining vector similarity search with keyword full-text search
- **Reciprocal Rank Fusion** — state-of-the-art result merging algorithm
- **Optical Character Recognition (OCR)** — making scanned documents searchable
- **JWT Authentication** with role-based access control
- **Containerized microservices** with Docker Compose
- **Reactive frontend** with real-time markdown rendering

The system is production-ready for a pilot deployment within the University of Rwanda environment.

---

*UniConnect — Connecting Students to Knowledge, Instantly.*
