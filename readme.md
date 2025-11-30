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
- **OpenAI GPT-4o-mini**: Natural language understanding
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
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_graph.py            # Graph tests
│
└── logs/                         # Application logs (gitignored)
    └── .gitkeep
```

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd inventorydb-agent
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# PostgreSQL Connection
DATABASE_URL=postgresql://username:password@host:port/database_name
```

### 5. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Basic Query

Simply describe what you want in plain English:

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

## Safety Features

- **Read-Only**: Only SELECT statements allowed
- **Query Timeout**: 20-second limit on execution
- **Schema Validation**: All tables/columns verified before execution
- **No Data Modification**: INSERT, UPDATE, DELETE, DROP all blocked
- **Error Handling**: Clear error messages for debugging

## Configuration

Edit `config.py` to customize:

```python
DEFAULT_MODEL = "gpt-4.1-nano"           # OpenAI model
DEFAULT_TEMPERATURE = 0.3               # LLM temperature
DEFAULT_DISPLAY_CAP = 500               # Max rows displayed
QUERY_TIMEOUT_SECONDS = 20              # Query timeout
```

## Development

### Running Tests

```bash
pytest tests/
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

## Troubleshooting

### Connection Issues

If you see connection errors:
1. Check `.env` file exists and has correct credentials
2. Verify PostgreSQL is running and accessible
3. Test connection: `psql $DATABASE_URL`

### SQL Generation Errors

If SQL generation fails:
- Check that table/column names are spelled correctly
- Verify schema is being retrieved (check logs)
- Try simplifying your query

### No Insights Generated

Insights are optional and only generated when:
- Results contain numeric data (3+ rows)
- Query keywords suggest analysis (trend, compare, etc.)
- Results are empty (explains why)

## Logging

Logs are written to `logs/inventorydb_agent.log` and include:
- Schema retrieval events
- Prompt improvements
- SQL generation
- Query execution times
- Errors and warnings

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues or questions:
- Check logs in `logs/inventorydb_agent.log`
- Review error messages in the Streamlit UI
- Open an issue on GitHub