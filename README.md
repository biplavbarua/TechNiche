# TechNiche - Legal AI Assistant

**TechNiche** is an advanced AI-powered legal assistant designed specifically for **Indian startups and SMEs**. It provides preliminary legal advice, risk analysis, and compliance insights with a focus on **Indian Law** across all domains.

Powered by **RAG (Retrieval-Augmented Generation)** with **Temporal Conflict Resolution**, TechNiche bases its advice on actual legal cases, automatically marking overruled precedents and ensuring only current law informs its responses. It also features a **Continuous Learning** system that allows it to autonomously ingest new legal precedents from the web.

## 🚀 Key Features

- **💡 Idea Risk Analysis**: Analyze your startup idea for potential legal pitfalls under Indian law.
- **🔍 Intelligent Search**: Query the legal database for specific concepts, cases, or statutes.
- **📚 Continuous Learning**: The system learns from new case URLs, keeping its knowledge base up-to-date locally or via high-performance vector DBs (Pinecone).
- **⚡ Real-time Citations**: Every piece of advice is backed by distinct citations from relevant, verified legal cases rendered dynamically on the UI.
- **🎨 Modern Enterprise Interface**: A responsive, clean Slate/Zinc light-theme UI designed for clarity and legal professionals, built with Next.js 15.
- **⚖️ Temporal Conflict Resolution**: Automatically detects when a new judgment overrules a prior case, verifies chronological ordering, and marks superseded law.
- **🛡️ Citation Verification**: Post-generation cross-referencing ensures LLM responses only cite actually-retrieved cases and surfaces the specific paragraphs cited to the user.

## 🌟 Patentable Innovation

TechNiche introduces a novel backend architecture designed for accuracy in legal AI, mitigating common LLM hallucinations through structured constraints. We plan to file a patent for our **Temporal Conflict Resolution & Verifiable Retrieval Engine**, which uniquely acts to:
1. **Timestamped Lexical Overruling**: Programmatically detects overriding precedent using a multi-agent chronological verification mechanism. Law gets deprecated dynamically based strictly on temporal validity without deleting history.
2. **Deterministic Citation Bounding**: Forces the LLM to restrict generated legal advice and strictly bind it to specific, retrieved chunk passages from the vector database. Any deviation correctly flags unverified citations.
3. **Structured Pydantic Extraction Loop**: Validates exact matches of case titles, dates, and overruled nodes during the continuous learning ingestion phase before saving to Pinecone. 

### Tech Stack

### Frontend
- **Framework**: [Next.js 15](https://nextjs.org/) (App Router)
- **Styling**: [TailwindCSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Animations**: [Framer Motion](https://www.framer.com/motion/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: Python 3.9+
- **Vector Store**: [ChromaDB](https://www.trychroma.com/) (Persistent)
- **AI Models**: OpenRouter (multi-model fallback cascade with 10 free models)
- **Extraction**: Pydantic-validated structured output from LLMs
- **Scraping**: BeautifulSoup4 & Requests

## ⚙️ Setup Instructions

### Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- An OpenRouter API Key ([Get one free](https://openrouter.ai/))

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "OPENROUTER_API_KEY=your_api_key_here" > .env

# Run the server
uvicorn app.main:app --reload
```
The backend will be available at `http://localhost:8000`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```
The frontend will be available at `http://localhost:3000`.

### 3. Run Tests

```bash
cd backend
source .venv/bin/activate
python3 -m pytest tests/ -v
```

## 🧠 How It Works

TechNiche uses a specialized RAG pipeline with four novel layers:

1. **Ingestion**: Legal cases are scraped and split into overlapping chunks (1500 chars, 200 overlap) for complete document coverage.
2. **Extraction**: Each document passes through Pydantic-validated AI extraction to capture case name, judgment date, overruled cases, and legal domain.
3. **Temporal Conflict Resolution**: When a new case overrules old precedent, the system verifies chronological ordering before marking superseded law — preventing data corruption from LLM hallucination.
4. **Retrieval + Generation**: User queries retrieve active-only cases, the legal domain is auto-detected for specialized prompting, and citations are cross-verified against actually-retrieved documents.

**Continuous Learning**: Feed specific URLs via the `/api/learn/url` endpoint or let the crawler discover new cases autonomously.

## 📜 License

This project is licensed under the MIT License.