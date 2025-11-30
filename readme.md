# 🗄️ InventoryDB Agent

Natural Language to SQL conversion using LangGraph and OpenAI. Convert plain English queries into PostgreSQL SELECT statements, execute them safely, and get AI-generated insights.

## Features

- **Natural Language Interface**: Describe what you want in plain English
- **Intelligent Prompt Improvement**: Clarifies vague requests before SQL generation
- **PostgreSQL-Specific**: Handles PostgreSQL syntax rules correctly
- **Read-Only Safety**: Only SELECT queries allowed, with timeout protection
- **AI-Powered Insights**: Automatic analysis of query results
- **Schema-Aware**: Validates all tables and columns against your database

## Architecture

```
User Input → Schema Retrieval → Prompt Improvement → SQL Generation → 
Query Execution → Results Display → Insights Generation
```

Built with:
- **LangGraph**: Workflow orchestration
- **SQLAlchemy**: Database interactions
- **Streamlit**: User interface
- **Pandas**: Data handling

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
    └── .gitkeep
```

---

## Setup Options

Choose one of three setup modes:

### **Option 1: Quick Start with Demo Database** (Recommended for Testing)

Try the app immediately with pre-populated sample data.

```bash
# 1. Clone and enter directory
git clone [<repo-url>](https://github.com/arbaazali872/Database_Query_Assistant.git)
cd database_query_assistant

# 2. Create .env file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start with demo database
docker-compose --profile demo up

# App runs at: http://localhost:8501
# Demo DB at: localhost:55432
# Credentials: demo/demo/inventorydb_demo
```

**What you get:**
- ✅ Streamlit app ready to use
- ✅ PostgreSQL with sample data (clients, projects, orders)
- ✅ No database setup needed

---

### **Option 2: Use Your Own External Database**

Connect to your existing PostgreSQL database.

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd inventorydb-agent

# 2. Configure .env
cp .env.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://user:password@your-host:5432/your-database
```

```bash
# 3. Start app only (no local database)
docker-compose up app

# App runs at: http://localhost:8501
```

**What you get:**
- ✅ Streamlit app connected to your database
- ✅ No local PostgreSQL container
- ✅ Works with any accessible PostgreSQL instance

---

### **Option 3: Local PostgreSQL (Clean Database)**

Start a local PostgreSQL database without pre-populated data.

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd inventorydb-agent

# 2. Create .env
cp .env.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://postgres:postgres@db:5432/inventorydb
```

```bash
# 3. Start with local database
docker-compose --profile localdb up

# App runs at: http://localhost:8501
# Local DB at: localhost:5432
```

**What you get:**
- ✅ Streamlit app
- ✅ Empty local PostgreSQL database
- ✅ You populate with your own data

---

## Manual Setup (Without Docker)

### 1. Clone and Install

```bash
git clone <your-repo-url>
cd inventorydb-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://user:password@host:port/database
```

### 3. Run Application

```bash
streamlit run app.py
```

Access at `http://localhost:8501`

---

## Usage

### Basic Query

```
Show me all projects from 2023 with their budgets and client names
```

### Query with Filters

```
List all orders over $10,000 from the last 6 months, sorted by amount
```

### Aggregation Query

```
What's the total budget by client industry?
```

### The app will:
1. ✅ Improve your prompt for clarity
2. ✅ Generate PostgreSQL-compliant SQL
3. ✅ Execute the query safely (read-only, with timeout)
4. ✅ Display results (up to 500 rows)
5. ✅ Generate insights automatically

---

## Docker Commands Reference

### Demo Mode
```bash
# Start demo environment
docker-compose --profile demo up

# Stop demo environment
docker-compose --profile demo down

# Rebuild after code changes
docker-compose --profile demo up --build
```

### Local Database Mode
```bash
# Start with local PostgreSQL
docker-compose --profile localdb up

# Stop and remove volumes (clears data)
docker-compose --profile localdb down -v
```

### External Database Mode
```bash
# Start app only
docker-compose up app

# Stop app
docker-compose down
```

### Useful Commands
```bash
# View logs
docker-compose logs -f app

# Shell into app container
docker exec -it inventorydb-agent bash

# Connect to demo database
docker exec -it inventorydb-postgres-demo psql -U demo -d inventorydb_demo

# Clean everything
docker-compose down -v
docker system prune -a
```

---

## Customizing Demo Data

To modify the demo database:

1. Edit `demo/init_demo.sql`
2. Rebuild:
```bash
docker-compose --profile demo down -v
docker-compose --profile demo up --build
```

---

## Safety Features

| Feature | Implementation |
|---------|----------------|
| **Read-Only** | Only SELECT statements allowed |
| **Timeout Protection** | 20-second query execution limit |
| **Schema Validation** | All tables/columns verified before execution |
| **SQL Injection Prevention** | Parameterized queries via SQLAlchemy |
| **Error Handling** | Graceful failures at every node |

---

## Configuration

Edit `config.py` to customize:

```python
DEFAULT_MODEL = "gpt-4o-mini"           # OpenAI model
DEFAULT_TEMPERATURE = 0.3               # LLM temperature
DEFAULT_DISPLAY_CAP = 500               # Max rows displayed
QUERY_TIMEOUT_SECONDS = 20              # Query timeout
```

---

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Adding New Nodes

1. Define node function in `src/nodes.py`
2. Add to workflow in `src/graph.py`
3. Update `src/state.py` if new state fields needed

### Modifying Prompts

Edit system prompts in `src/prompts.py`:
- `PROMPT_IMPROVER_SYSTEM`: Prompt improvement instructions
- `QUERY_GENERATOR_SYSTEM`: SQL generation rules
- `INSIGHTS_GENERATOR_SYSTEM`: Insights generation guidelines

---

## Troubleshooting

### Connection Issues

**Problem**: Can't connect to database

**Solution**:
1. Check `.env` file exists and has correct credentials
2. Verify PostgreSQL is running: `docker ps`
3. Check logs: `docker-compose logs -f`
4. Test connection: `psql $DATABASE_URL`

### Port Already in Use

**Problem**: `Error: port 8501 already in use`

**Solution**:
```bash
# Find and kill process on port 8501
lsof -ti:8501 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "8502:8501"  # Use port 8502 instead
```

### SQL Generation Errors

**Problem**: SQL generation fails

**Solution**:
- Check that table/column names are spelled correctly
- Verify schema is being retrieved (check logs)
- Try simplifying your query
- Check `logs/inventorydb_agent.log` for details

### Demo Database Not Populating

**Problem**: Demo database is empty

**Solution**:
```bash
# Remove old volume and restart
docker-compose --profile demo down -v
docker-compose --profile demo up

# Verify init_demo.sql exists
ls demo/init_demo.sql
```

---

## Logging

Logs are written to `logs/inventorydb_agent.log` and include:
- Schema retrieval events
- Prompt improvements
- SQL generation
- Query execution times
- Errors and warnings

View logs:
```bash
# Real-time logs
tail -f logs/inventorydb_agent.log

# Docker logs
docker-compose logs -f app
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required) | `sk-proj-...` |
| `DATABASE_URL` | PostgreSQL connection string (required) | `postgresql://user:pass@host:5432/db` |

---

## Production Deployment

### Security Checklist

- [ ] Use secrets management (not `.env` files)
- [ ] Enable SSL for `DATABASE_URL`
- [ ] Use read-only database user
- [ ] Set resource limits in docker-compose
- [ ] Enable HTTPS with reverse proxy (nginx)
- [ ] Configure proper logging and monitoring
- [ ] Disable debug mode in Streamlit

### Example Production DATABASE_URL

```bash
DATABASE_URL=postgresql://readonly_user:secure_pass@prod-db.example.com:5432/proddb?sslmode=require
```

---

## License

MIT License - see LICENSE file for details

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## Support

For issues or questions:
- Check logs in `logs/inventorydb_agent.log`
- Review error messages in the Streamlit UI
- Open an issue on GitHub

---

**Built with ❤️ using LangGraph | Read-only by design | Safe for production**