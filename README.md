# TechNiche - Legal AI Assistant

**TechNiche** is an advanced AI-powered legal assistant designed specifically for **Indian startups and SMEs**. It provides preliminary legal advice, risk analysis, and compliance insights with a focus on **Intellectual Property (IP) Law**.

Powered by **RAG (Retrieval-Augmented Generation)**, TechNiche bases its advice on actual legal cases and statutes, ensuring grounded and relevant responses. It also features a **Continuous Learning** system that allows it to autonomously ingest new legal precedents from the web.

## 🚀 Key Features

- **💡 Idea Risk Analysis**: Analyze your startup idea for potential legal pitfalls under Indian law.
- **🔍 Intelligent Search**: Query the legal database for specific concepts, cases, or statutes.
- **📚 Continuous Learning**: The system functionality allows it to learn from new case URLs, keeping its knowledge base up-to-date.
- **⚡ Real-time Citations**: Every piece of advice is backed by citations from relevant legal cases.
- **🎨 Modern Interface**: A responsive, dark-mode-enabled UI built with the latest web technologies.

## 🛠️ Tech Stack

### Frontend
- **Framework**: [Next.js 15](https://nextjs.org/) (App Router)
- **Styling**: [TailwindCSS v4](https://tailwindcss.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Animations**: [Framer Motion](https://www.framer.com/motion/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: Python 3.9+
- **Vector Store**: [ChromaDB](https://www.trychroma.com/) (Persistent)
- **AI Models**: Google Gemini (via `google-generativeai`) for Embeddings and Chat.
- **Scraping**: BeautifulSoup4 & Requests.

## ⚙️ Setup Instructions

### Prerequisites
- Node.js (v18+)
- Python (v3.9+)
- Docker (Optional, for backend)
- A Google Gemini API Key

### 1. Backend Setup

You can run the backend using Docker or directly on your machine.

**Option A: Using Docker (Recommended)**
```bash
# Create a .env file in backend/
echo "GOOGLE_API_KEY=your_api_key_here" > backend/.env

# Start with Docker Compose
docker-compose up --build
```

**Option B: Local Python Setup**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "GOOGLE_API_KEY=your_api_key_here" > .env

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

## 🧠 AI & continuous Learning

TechNiche uses a specialized RAG pipeline.
1. **Ingestion**: Legal cases are scraped, chunked, and embedded using Gemini's embedding models.
2. **Storage**: Embeddings are stored in a local ChromaDB instance.
3. **Retrieval**: User queries are embedded and compared against the vector store to find the most relevant legal context.
4. **Generation**: The LLM generates advice based on the retrieved context.

**New Feature**: You can feed specific URLS to the system via the `/api/learn/url` endpoint or let it crawl autonomously to expand its knowledge base.

## 📜 License

This project is licensed under the MIT License.