# Sasha Sales AI - LangGraph Implementation

Reimplementation of Sasha Sales AI using LangGraph for stateful workflow orchestration, LangChain for LLM-powered agents, and LangSmith for comprehensive observability.

## Features

- Email webhook ingestion
- Lead analysis with LLM
- Deterministic requirement validation
- Missing info clarification
- Feasibility checking
- Pricing calculation
- Approval gates (human-in-the-loop)
- Quote email generation
- Reply processing
- Order placement
- Confirmation emails
- State persistence with checkpointing
- REST API
- Full observability with LangSmith

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Required environment variables:
- `LANGSMITH_API_KEY`: Your LangSmith API key for observability
- `OPENAI_API_KEY`: Your OpenAI API key for LLM operations

## Usage

```bash
uvicorn src.sasha_sales_ai.main:app --reload
```

## API Endpoints

- `POST /webhook/email` - Process incoming email
- `POST /webhook/reply` - Process customer reply
- `POST /approve/{lead_id}` - Approve a quote
- `POST /reject/{lead_id}` - Reject a quote
- `GET /lead/{lead_id}` - Get lead status
- `GET /leads` - List all leads

## Project Structure

```
sasha-ai-agent-langGraph/
├── src/
│   └── sasha_sales_ai/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app with LangSmith setup
│       ├── graph.py                # LangGraph StateGraph with checkpoints
│       ├── state.py                # FlowState TypedDict definition
│       ├── config.py               # Configuration management
│       ├── logging_config.py       # LangSmith & Python logging setup
│       ├── nodes/                  # Graph node implementations
│       ├── chains/                 # LangChain LCEL chains
│       ├── tools/                  # LangChain tools
│       ├── flow_manager.py         # Graph instance management
│       ├── validators.py           # Deterministic validation
│       ├── api/                    # API routes and models
│       ├── storage/                # RAG storage
│       └── utils/                  # Utility functions
├── tests/                          # Test suite
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Observability

This project integrates LangSmith for comprehensive observability:

1. **Automatic Tracing**: All LangChain/LangGraph operations are automatically traced
2. **Custom Context**: Business logic is wrapped in tracing contexts
3. **Performance Metrics**: Latency, token usage, and cost tracking
4. **Error Tracking**: Exceptions are logged with full context
5. **Flow Visualization**: Complete workflow execution traces
6. **Checkpoint Inspection**: State snapshots at interrupt points

View traces at [smith.langchain.com](https://smith.langchain.com)
