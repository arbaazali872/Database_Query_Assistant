# 🗄️ InventoryDB Agent

Natural Language to SQL conversion using LangGraph and OpenAI. Convert plain English queries into PostgreSQL SELECT statements, execute them safely, and get AI-generated insights.

## Features

- Natural Language Interface
- ReAct Agent Pattern (autonomous tool selection)
- PostgreSQL-Specific SQL Generation
- Read-Only Safety (20s timeout)
- AI-Powered Insights
- Schema Validation

## Architecture

```
User Input → ReAct Agent (reasoning & tool calls loop) → 
Query Execution → Results Display → Insights Generation
```

### Workflow Diagram

![Workflow Diagram](assets/flow_diagram_langgraph.png)


**Tech Stack**: LangGraph, OpenAI GPT-4.1-nano SDK, SQLAlchemy, Streamlit, Pandas

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
│   ├── graph.py                 # ReAct agent graph definition
│   ├── state.py                 # State schema definition
│   ├── tools.py                 # Agent tools
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

### 1. Clone and Setup

```bash
git clone https://github.com/arbaazali872/Database_Query_Assistant.git
cd database_query_assistant
```

Create `.env` file:
```bash
# Required for all modes
OPENAI_API_KEY=your_key_here

# Required for Local Database mode
DATABASE_URL=postgresql://postgres:postgres@db:5432/inventorydb

# Required for External Database mode (Replace with your own)
DATABASE_URL=postgresql://user:password@host:5432/database
```

**Note:** Demo mode only needs `OPENAI_API_KEY` (DATABASE_URL is auto-configured)

### 2. Choose Your Mode

**Demo Mode** - Try it with pre-populated sample data
```bash
docker-compose --profile demo up
```

**Local Database** - Start with an empty PostgreSQL database
```bash
docker-compose --profile localdb up
```

**External Database** - Connect to your existing database
```bash
docker-compose up app
```

### 3. Access the App

Open your browser: **http://localhost:8501**

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
1. Retrieve schema
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

**Built with LangGraph | Read-only by design**