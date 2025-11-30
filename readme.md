# 🗄️ InventoryDB Agent

Natural Language to SQL conversion using LangGraph and OpenAI. Convert plain English queries into PostgreSQL SELECT statements, execute them safely, and get AI-generated insights.

## Features

- Natural Language Interface
- Intelligent Prompt Improvement
- PostgreSQL-Specific SQL Generation
- Read-Only Safety (20s timeout)
- AI-Powered Insights
- Schema Validation

## Architecture

```
User Input → Schema Retrieval → Prompt Improvement → SQL Generation → 
Query Execution → Results Display → Insights Generation
```

**Tech Stack**: LangGraph, SQLAlchemy, Streamlit, Pandas

## Project Structure

```
inventorydb-agent/
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Template for environment setup
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── config.py                     # Configuration and initialization
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker orchestration
│
├── src/                          # Core source code
│   ├── __init__.py              # Package initialization
│   ├── nodes.py                 # LangGraph node implementations
│   ├── graph.py                 # LangGraph workflow definition
│   ├── state.py                 # State schema definition
│   ├── prompts.py               # LLM system prompts
│   └── utils.py                 # Helper functions
│
├── app.py                        # Streamlit application
│
├── demo/                         # Demo database files
│   └── init_demo.sql            # Pre-populated test data
│
│
└── logs/                         # Application logs (gitignored)
```

---

## Quick Start with Docker

### Three Profiles Available:

**1. Demo Mode** - Pre-populated test database
```bash
docker-compose --profile demo up
```
- App: http://localhost:8501
- DB: localhost:55432 (demo/demo/inventorydb_demo)

**2. Local DB** - Empty PostgreSQL database
```bash
docker-compose --profile localdb up
```
- App: http://localhost:8501
- DB: localhost:5432 (postgres/postgres/inventorydb)

**3. External DB** - Use your own database
```bash
docker-compose up app
```
- App: http://localhost:8501
- Connects to your DATABASE_URL

### Setup

1. **Clone repository**
```bash
git clone https://github.com/arbaazali872/Database_Query_Assistant.git
cd database_query_assistant

```

2. **Create `.env` file**
```bash
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@host:5432/database
```

3. **Choose a profile and run**
```bash
docker-compose --profile demo up
```

---

## Manual Setup (Without Docker)

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://user:password@host:5432/database

# Run
streamlit run app.py
```

---

## Usage Examples

```
Show me all projects from 2023 with their budgets and client names
```

```
List all orders over $10,000 from the last 6 months
```

```
What's the total budget by client industry?
```

The app will:
1. Clarify your request
2. Generate PostgreSQL SQL
3. Execute safely (read-only)
4. Display results (500 row cap)
5. Generate insights

---

## Troubleshooting

**SQL Generation Fails**
- Verify table/column names are correct
- Check schema is being retrieved
- Simplify your query
- Review logs at `logs/inventorydb_agent.log`

---

## Configuration

Edit `config.py`:
```python
DEFAULT_MODEL = "gpt-4.1-nano"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_DISPLAY_CAP = 500
QUERY_TIMEOUT_SECONDS = 20
```

---

## License

MIT License

---

**Built with ❤️ using LangGraph | Read-only by design | Safe for production**