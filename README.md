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
- State persistence with Redis
- REST API
- Full observability with LangSmith
- Docker support for easy deployment

## Quick Start (Docker - Recommended)

The fastest way to get started is using Docker Compose, which runs both the app and Redis together.

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd sasha-ai-agent-langGraph

# Create .env file with your API keys
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
EOF
```

### 2. Start with Docker Compose

```bash
# Build and start all services (app + Redis)
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

### 3. Verify Everything is Running

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "langsmith_enabled": true,
  "redis_connected": true,
  "lead_count": 0,
  "checkpointer_type": "RedisSaver"
}
```

### 4. Stop the Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v
```

## Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up --build` | Build and start all services |
| `docker-compose up -d` | Start in background (detached) |
| `docker-compose down` | Stop all services |
| `docker-compose down -v` | Stop and remove volumes |
| `docker-compose logs -f` | View logs (follow mode) |
| `docker-compose logs -f app` | View only app logs |
| `docker-compose ps` | List running containers |
| `docker-compose restart app` | Restart only the app |

### Development Mode (Hot Reload)

For development with live code reloading:

```bash
# Use the development compose file
docker-compose -f docker-compose.dev.yml up --build
```

This mounts your `src/` directory, so changes are reflected immediately without rebuilding.

---

## Manual Installation (Without Docker)

If you prefer not to use Docker, follow these steps:

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Prerequisites

#### Redis Setup (Required for State Persistence)

This project uses Redis for both lead state storage and LangGraph checkpointing.

**Option 1: Docker (Recommended)**
```bash
# Start Redis container
docker run -d --name redis -p 6379:6379 redis:latest

# Verify it's running
docker ps | grep redis

# Stop when done
docker stop redis
```

**Option 2: macOS with Homebrew**
```bash
# Install Redis
brew install redis

# Start Redis service
brew services start redis

# Verify connection
redis-cli ping  # Should return: PONG

# Stop when done
brew services stop redis
```

**Option 3: Linux**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Verify
redis-cli ping
```

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Required: API Keys
LANGSMITH_API_KEY=your_langsmith_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Required: Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_KEY_PREFIX=sasha:

# Optional: LangSmith Settings
LANGSMITH_PROJECT=sasha-ai-agent-langGraph
LANGSMITH_TRACING=true

# Optional: LLM Settings
MODEL_NAME=gpt-4o-mini

# Optional: API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Business Rules
APPROVAL_THRESHOLD=10000.0
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM operations |
| `LANGSMITH_API_KEY` | Yes | - | LangSmith API key for observability |
| `REDIS_URL` | Yes | `redis://localhost:6379` | Redis connection URL |
| `REDIS_KEY_PREFIX` | No | `sasha:` | Prefix for all Redis keys |
| `LANGSMITH_PROJECT` | No | `sasha-ai-agent-langGraph` | LangSmith project name |
| `LANGSMITH_TRACING` | No | `true` | Enable/disable tracing |
| `MODEL_NAME` | No | `gpt-4o-mini` | OpenAI model to use |
| `API_HOST` | No | `0.0.0.0` | API server host |
| `API_PORT` | No | `8000` | API server port |
| `APPROVAL_THRESHOLD` | No | `10000.0` | Amount above which requires approval |

### Start the Application (Manual)

**1. Start Redis (if not already running)**
```bash
docker run -d --name redis -p 6379:6379 redis:latest
```

**2. Start the API server**
```bash
uvicorn src.sasha_sales_ai.main:app --reload
```

**3. Verify health (including Redis connection)**
```bash
curl http://localhost:8000/api/v1/health
```

---

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Send a new lead email (creates a new lead)
curl -X POST http://localhost:8000/api/v1/webhook/email \
  -H "Content-Type: application/json" \
  -d '{
    "from_email": "customer@example.com",
    "subject": "Inquiry about product",
    "body": "I need 100 black t-shirts with logo printing in 1 week. Can you do that?"
  }'

# Get lead status (use lead_id from previous response)
curl http://localhost:8000/api/v1/lead/lead-abc12345

# List all leads
curl http://localhost:8000/api/v1/leads

# Send a reply email (customer confirms order)
curl -X POST http://localhost:8000/api/v1/webhook/reply \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "lead-2a1d3f5a",
    "from_email": "customer@example.com",
    "subject": "Re: Your Quote",
    "body": "Yes, I confirm the order. Please proceed.",
    "email_type": "reply"
  }'

# Send a clarification reply (customer provides more details)
curl -X POST http://localhost:8000/api/v1/webhook/reply \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "lead-2a1d3f5a",
    "from_email": "customer@example.com",
    "subject": "Re: Need more information",
    "body": "Thanks for getting back to me. I will be needing this order at 222 Broadway, NYC. The material would be pure cotton and you can send 50 in size M and 50 in size L.",
    "email_type": "reply"
  }'

# Send another clarification with logo details
curl -X POST http://localhost:8000/api/v1/webhook/reply \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "lead-2a1d3f5a",
    "from_email": "customer@example.com",
    "subject": "Re: Logo Details",
    "body": "I need a very simple logo of my company in White color at the top right corner of the shirt above the pocket.",
    "email_type": "reply"
  }'

# Approve a pending quote (if approval is required)
curl -X POST http://localhost:8000/api/v1/approve/lead-abc12345 \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "manager@sasha.com",
    "notes": "Approved for priority processing"
  }'

# Reject a pending quote
curl -X POST http://localhost:8000/api/v1/reject/lead-abc12345 \
  -H "Content-Type: application/json" \
  -d '{
    "approved_by": "manager@sasha.com",
    "notes": "Price too low for this quantity"
  }'

# Get pending approvals
curl http://localhost:8000/api/v1/approvals/pending

# Delete a lead (for testing/cleanup)
curl -X DELETE http://localhost:8000/api/v1/lead/lead-abc12345
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
│       ├── flow_manager.py         # Graph instance management with Redis
│       ├── validators.py           # Deterministic validation
│       ├── api/                    # API routes and models
│       ├── storage/
│       │   ├── rag_storage.py      # RAG storage implementation
│       │   └── redis_store.py      # Redis state storage for leads
│       └── utils/                  # Utility functions
├── tests/                          # Test suite
├── Dockerfile                      # Production Docker image
├── docker-compose.yml              # Production compose (app + Redis)
├── docker-compose.dev.yml          # Development compose with hot-reload
├── .dockerignore                   # Docker build exclusions
├── requirements.txt
├── pyproject.toml
└── README.md
```

## State Persistence Architecture

This project uses **Redis** for production-grade state persistence:

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Redis                                │
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │   Lead States        │  │   LangGraph Checkpoints      │  │
│  │   (sasha:lead:*)     │  │   (Managed by RedisSaver)    │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐         ┌─────────┐          ┌─────────┐
   │ API     │         │ Worker  │          │ Instance│
   │ Server  │         │    2    │          │    N    │
   └─────────┘         └─────────┘          └─────────┘
```

### Components

1. **RedisStateStore** (`storage/redis_store.py`)
   - Stores lead state as JSON strings
   - Key pattern: `{prefix}lead:{lead_id}`
   - Supports CRUD operations and filtering
   - Thread-safe and supports multiple instances

2. **RedisSaver** (LangGraph Checkpointer)
   - Persists LangGraph checkpoints to Redis
   - Enables flow resumption after server restarts
   - Supports human-in-the-loop interrupt points

### Benefits

- **Persistence**: State survives server restarts
- **Scalability**: Multiple app instances can share state
- **Performance**: Sub-millisecond read/write operations
- **Reliability**: Redis persistence options (RDB/AOF)

## Observability

This project integrates LangSmith for comprehensive observability:

1. **Automatic Tracing**: All LangChain/LangGraph operations are automatically traced
2. **Custom Context**: Business logic is wrapped in tracing contexts
3. **Performance Metrics**: Latency, token usage, and cost tracking
4. **Error Tracking**: Exceptions are logged with full context
5. **Flow Visualization**: Complete workflow execution traces
6. **Checkpoint Inspection**: State snapshots at interrupt points

View traces at [smith.langchain.com](https://smith.langchain.com)

## Code Flow & Architecture

### LangGraph Workflow Flow

The following diagram illustrates the complete code flow through the LangGraph state machine:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SALES WORKFLOW FLOW                                 │
└─────────────────────────────────────────────────────────────────────────────┘

START: Email Received (via POST /api/v1/webhook/email)
  │
  ▼
┌─────────────────┐
│  ingest_email   │  • Parse email data (from, subject, body)
│   (nodes/       │  • Determine email type (new vs reply)
│   ingest.py)    │  • Load thread history if available
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ understand_lead│  • Analyze email with LLM
│   (nodes/       │  • Extract requirements (structured output)
│  understand.py) │  • Validate required fields
                  │  • Identify missing information
                  │  • Classify customer intent
└────────┬────────┘
         │
         ├─────────────────────────────────────────────────┐
         │                                                 │
         ▼                                                 ▼
    ┌─────────┐                                    ┌──────────────┐
    │ REPLY?  │                                    │  NEW EMAIL   │
    └────┬────┘                                    └──────┬───────┘
         │                                                 │
         │                                                 ├──────────────────┐
         │                                                 │                  │
         ▼                                                 ▼                  ▼
┌─────────────────┐                          ┌────────────────────┐  ┌──────────────┐
│ process_reply   │                          │request_clarification│  │check_feasible│
│   (nodes/       │                          │   (nodes/           │  │   (nodes/    │
│   reply.py)     │                          │clarification.py)    │  │feasibility.py│
└────────┬────────┘                          └──────────┬─────────┘  └──────┬───────┘
         │                                              │                    │
         │                                              │                    │
         │                                              │                    ├──────────┐
         │                                              │                    │          │
         │                                              │                    ▼          ▼
         │                                              │            ┌──────────────┐  ┌──────────────┐
         │                                              │            │   FEASIBLE?  │  │handle_reject │
         │                                              │            └──────┬───────┘  │   (nodes/    │
         │                                              │                   │          │rejection.py) │
         │                                              │                   │ YES      └──────┬───────┘
         │                                              │                   │                  │
         │                                              │                   ▼                  │
         │                                              │            ┌──────────────┐         │
         │                                              │            │calculate_price│         │
         │                                              │            │   (nodes/    │         │
         │                                              │            │  pricing.py) │         │
         │                                              │            └──────┬───────┘         │
         │                                              │                   │                  │
         │                                              │                   ▼                  │
         │                                              │            ┌──────────────┐         │
         │                                              │            │check_approval│         │
         │                                              │            │   (nodes/    │         │
         │                                              │            │ approval.py) │         │
         │                                              │            └──────┬───────┘         │
         │                                              │                   │                  │
         │                                              │                   ├──────────┐       │
         │                                              │                   │          │       │
         │                                              │                   ▼          ▼       │
         │                                              │            ┌──────────────┐ ┌──────────────┐
         │                                              │            │NEEDS APPROVAL│ │  send_quote  │
         │                                              │            └──────┬───────┘ │   (nodes/    │
         │                                              │                   │         │   quote.py)  │
         │                                              │                   │ YES     └──────┬───────┘
         │                                              │                   │                 │
         │                                              │                   ▼                 │
         │                                              │            ┌──────────────┐        │
         │                                              │            │request_approval│        │
         │                                              │            │   (nodes/     │        │
         │                                              │            │ approval.py)  │        │
         │                                              │            └──────┬─────────┘        │
         │                                              │                   │                   │
         │                                              │                   │                   │
         │                                              ▼                   ▼                   ▼
         │                                    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
         │                                    │ END: Wait for   │  │ END: Wait for   │  │ END: Wait for   │
         │                                    │  Customer Reply │  │   Approval      │  │  Customer Reply │
         │                                    │  (CLARIFYING)   │  │(APPROVAL_PENDING│  │  (QUOTE_SENT)   │
         │                                    └─────────────────┘  └─────────────────┘  └─────────────────┘
         │
         │
         │  CUSTOMER INTENT ROUTING (from process_reply):
         │
         ├─────────────────────────────────────────────────────────────────────┐
         │                                                                     │
         │  ┌──────────────────────────────────────────────────────────────┐  │
         │  │ Customer Intent Classification:                              │  │
         │  │                                                              │  │
         │  │  • CONFIRMATION  → place_order                              │  │
         │  │  • REJECTION     → handle_rejection                         │  │
         │  │  • MODIFICATION  → check_feasibility (recalculate)         │  │
         │  │  • QUESTION/     → request_clarification                    │  │
         │  │    CLARIFICATION                                            │  │
         │  └──────────────────────────────────────────────────────────────┘  │
         │                                                                     │
         └─────────────────────────────────────────────────────────────────────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │ place_order  │
                                                          │   (nodes/    │
                                                          │   order.py)  │
                                                          └──────┬───────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │send_confirm  │
                                                          │   (nodes/    │
                                                          │confirmation  │
                                                          │    .py)      │
                                                          └──────┬───────┘
                                                                 │
                                                                 ▼
                                                          ┌──────────────┐
                                                          │ END: Completed│
                                                          │  (COMPLETED)  │
                                                          └──────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLOW RESUMPTION POINTS                            │
└─────────────────────────────────────────────────────────────────────────────┘

1. CLARIFYING → Customer sends reply → POST /api/v1/webhook/reply → process_reply
2. APPROVAL_PENDING → Human approves → POST /api/v1/approve/{lead_id} → send_quote
3. QUOTE_SENT → Customer sends reply → POST /api/v1/webhook/reply → process_reply


┌─────────────────────────────────────────────────────────────────────────────┐
│                            STATE TRANSITIONS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

NEW → UNDERSTANDING → CLARIFYING → (wait for reply) → UNDERSTANDING → ...
NEW → UNDERSTANDING → FEASIBILITY → PRICING → APPROVAL_PENDING → (wait) → QUOTE_SENT → (wait) → ORDER_PLACED → COMPLETED
NEW → UNDERSTANDING → FEASIBILITY → REJECTED
QUOTE_SENT → (reply: confirmation) → ORDER_PLACED → COMPLETED
QUOTE_SENT → (reply: rejection) → REJECTED
QUOTE_SENT → (reply: modification) → FEASIBILITY → PRICING → ...
QUOTE_SENT → (reply: question) → CLARIFYING → (wait) → ...
```

### Detailed Flow Steps

#### 1. **Entry Point** (`main.py`)
   - FastAPI application starts with lifespan handler
   - Initializes LangSmith observability
   - Sets up FlowManager singleton
   - Registers API routes

#### 2. **API Layer** (`api/routes.py`)
   - **POST `/api/v1/webhook/email`**: Entry point for new emails
     - Creates/updates FlowState
     - Triggers graph execution via FlowManager
   - **POST `/api/v1/webhook/reply`**: Entry point for customer replies
     - Updates existing FlowState with reply data
     - Resumes graph execution
   - **POST `/api/v1/approve/{lead_id}`**: Human approval endpoint
     - Updates state with approval decision
     - Resumes graph from interrupt point

#### 3. **Flow Manager** (`flow_manager.py`)
   - Manages LangGraph instance lifecycle
   - Handles state persistence (JSON files)
   - Provides checkpoint management
   - Coordinates graph execution with thread_id

#### 4. **Graph Definition** (`graph.py`)
   - Creates StateGraph with FlowState schema
   - Defines all nodes and conditional edges
   - Sets up interrupt points (before approval)
   - Compiles graph with MemorySaver checkpointer

#### 5. **Node Execution Flow**

   **a. `ingest_email`** (`nodes/ingest.py`)
   - Parses email data
   - Extracts metadata (from, subject, body)
   - Determines email type (new vs reply)
   - Loads thread history if available

   **b. `understand_lead`** (`nodes/understand.py`)
   - Uses LLM chain to analyze email content
   - Extracts requirements using structured output
   - Validates required fields (deterministic)
   - Identifies missing information
   - Classifies customer intent

   **c. `request_clarification`** (`nodes/clarification.py`)
   - Generates clarification email using LLM
   - Updates status to CLARIFYING
   - Sends email via email tool
   - Flow ends, waiting for customer reply

   **d. `check_feasibility`** (`nodes/feasibility.py`)
   - Uses feasibility tool to validate requirements
   - Checks against business rules
   - Determines if request is feasible
   - Provides alternatives if not feasible

   **e. `calculate_pricing`** (`nodes/pricing.py`)
   - Uses pricing tool/chain to calculate quote
   - Applies pricing rules and discounts
   - Generates detailed pricing breakdown
   - Updates state with price_quote

   **f. `check_approval`** (`nodes/approval.py`)
   - Checks if quote requires approval
   - Based on amount thresholds or business rules
   - Sets needs_approval flag

   **g. `request_approval`** (`nodes/approval.py`)
   - Updates status to APPROVAL_PENDING
   - Flow interrupts here (human-in-the-loop)
   - API endpoint allows approval/rejection

   **h. `send_quote`** (`nodes/quote.py`)
   - Generates professional quote email
   - Includes pricing details and terms
   - Sends via email tool
   - Updates status to QUOTE_SENT
   - Flow ends, waiting for customer reply

   **i. `process_reply`** (`nodes/reply.py`)
   - Analyzes customer reply email
   - Classifies intent (confirmation, rejection, modification, question)
   - Updates requirements if modification
   - Routes to appropriate next step

   **j. `place_order`** (`nodes/order.py`)
   - Uses order tool to create order
   - Generates order ID
   - Updates status to ORDER_PLACED

   **k. `send_confirmation`** (`nodes/confirmation.py`)
   - Generates order confirmation email
   - Includes order details and tracking
   - Sends via email tool
   - Updates status to COMPLETED

   **l. `handle_rejection`** (`nodes/rejection.py`)
   - Generates polite rejection email
   - Updates status to REJECTED
   - Flow ends

#### 6. **State Management** (`state.py`)
   - FlowState TypedDict defines all state fields
   - State flows through graph nodes
   - Checkpointed at interrupt points
   - Persisted to disk by FlowManager

#### 7. **Tools & Chains** (`tools/`, `chains/`)
   - **Email Tool**: Sends emails via external service
   - **Feasibility Tool**: Validates requirements
   - **Pricing Tool**: Calculates quotes
   - **Order Tool**: Creates orders
   - **LLM Chains**: LangChain LCEL chains for LLM operations

#### 8. **Observability** (`utils/langsmith_helpers.py`)
   - All operations wrapped in LangSmith tracing
   - Automatic trace collection
   - Custom metadata and tags
   - Performance metrics tracking

### State Transitions

```
NEW → UNDERSTANDING → CLARIFYING (wait) → UNDERSTANDING
NEW → UNDERSTANDING → FEASIBILITY → PRICING → APPROVAL_PENDING (wait) → QUOTE_SENT (wait) → ORDER_PLACED → COMPLETED
NEW → UNDERSTANDING → FEASIBILITY → REJECTED
QUOTE_SENT → (reply) → ORDER_PLACED → COMPLETED
QUOTE_SENT → (reply) → REJECTED
QUOTE_SENT → (reply) → FEASIBILITY → (recalculate)
```

### Key Design Patterns

1. **State Machine**: LangGraph provides stateful workflow orchestration
2. **Checkpointing**: State persisted at interrupt points for resumability
3. **Human-in-the-Loop**: Approval gates pause flow for human decision
4. **Conditional Routing**: Dynamic routing based on state values
5. **Async Execution**: All graph operations are async
6. **Observability**: Full tracing with LangSmith integration

## Deployment to Render

### Prerequisites

- Render account ([render.com](https://render.com))
- GitHub repository with your code
- Environment variables ready (API keys)

### Step-by-Step Deployment

#### 1. **Prepare Your Repository**

Ensure your repository has:
- `requirements.txt` with all dependencies
- `pyproject.toml` (optional but recommended)
- `.env.example` file (for reference, not deployed)
- Proper Python version specified

#### 2. **Create a Render Web Service**

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select the repository containing this project

#### 3. **Configure Build Settings**

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn src.sasha_sales_ai.main:app --host 0.0.0.0 --port $PORT
```

**Environment:**
- Select **Python 3**
- Render will auto-detect Python version from `pyproject.toml` or `requirements.txt`

#### 4. **Set Environment Variables**

In the Render dashboard, add these environment variables:

**Required:**
```
LANGSMITH_API_KEY=your_langsmith_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Optional (with defaults):**
```
API_HOST=0.0.0.0
API_PORT=8000
STATE_STORAGE_PATH=/opt/render/project/src/.state
LOG_LEVEL=INFO
```

**Note**: Render provides `$PORT` automatically - use it in the start command.

#### 5. **Configure Advanced Settings**

**Instance Type:**
- Start with **Free** tier for testing
- Upgrade to **Starter** ($7/month) or **Standard** ($25/month) for production

**Health Check Path:**
```
/api/v1/health
```

**Auto-Deploy:**
- Enable **"Auto-Deploy"** to deploy on every push to main branch
- Or disable for manual deployments

#### 6. **Deploy**

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Install dependencies
   - Start your application
   - Provide a public URL (e.g., `https://sasha-sales-ai.onrender.com`)

#### 7. **Verify Deployment**

1. Check the **Logs** tab for startup messages
2. Visit `https://your-app.onrender.com/api/v1/health`
3. Should return:
   ```json
   {
     "status": "healthy",
     "version": "0.1.0",
     "langsmith_enabled": true
   }
   ```

#### 8. **Configure Custom Domain (Optional)**

1. Go to **Settings** → **Custom Domain**
2. Add your domain
3. Follow DNS configuration instructions
4. SSL certificate is automatically provisioned

### Render-Specific Considerations

#### State Persistence

Render's filesystem is **ephemeral** - files are lost on restart. For production:

1. **Use External Storage** (Recommended):
   - Configure `STATE_STORAGE_PATH` to use S3, Redis, or PostgreSQL
   - Update `flow_manager.py` to use persistent storage

2. **Use Render Disk** (Alternative):
   - Add a **Disk** service in Render
   - Mount it and update `STATE_STORAGE_PATH`

#### Database Integration (Future)

For persistent state storage, consider:

1. **PostgreSQL** (Render Managed):
   - Create a PostgreSQL database in Render
   - Use SQLite checkpointer with PostgreSQL adapter
   - Update `graph.py` to use SQLite checkpointer

2. **Redis** (Render Managed):
   - Create a Redis instance
   - Use Redis-based checkpointer
   - Better for high-throughput scenarios

#### Environment-Specific Configuration

Create a `render.yaml` file for Infrastructure as Code:

```yaml
services:
  - type: web
    name: sasha-sales-ai
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn src.sasha_sales_ai.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: LANGSMITH_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: API_HOST
        value: 0.0.0.0
      - key: LOG_LEVEL
        value: INFO
    healthCheckPath: /api/v1/health
```

Then deploy via Render Dashboard → **"New +"** → **"Blueprint"** → Upload `render.yaml`

### Monitoring & Logs

1. **View Logs**: Dashboard → Your Service → **Logs** tab
2. **Metrics**: Dashboard → Your Service → **Metrics** tab
   - CPU usage
   - Memory usage
   - Request rate
   - Response times
3. **LangSmith**: All traces available at [smith.langchain.com](https://smith.langchain.com)

### Troubleshooting

**Common Issues:**

1. **Build Fails**:
   - Check `requirements.txt` syntax
   - Verify Python version compatibility
   - Check build logs for specific errors

2. **App Crashes on Start**:
   - Verify all environment variables are set
   - Check start command uses `$PORT`
   - Review logs for import errors

3. **State Not Persisting**:
   - Remember filesystem is ephemeral
   - Implement external storage solution

4. **Health Check Fails**:
   - Verify health endpoint path
   - Check if app is binding to `0.0.0.0`
   - Ensure port matches `$PORT`

### Cost Estimation

- **Free Tier**: 750 hours/month (suitable for testing)
- **Starter**: $7/month (512MB RAM, 0.5 CPU)
- **Standard**: $25/month (2GB RAM, 1 CPU) - Recommended for production

### Security Best Practices

1. **Never commit secrets**: Use Render environment variables
2. **Enable HTTPS**: Automatic with Render (always on)
3. **Rate Limiting**: Consider adding rate limiting middleware
4. **CORS**: Update CORS settings in `main.py` for production
5. **API Keys**: Rotate keys regularly
6. **Monitoring**: Set up alerts in Render dashboard

### Next Steps After Deployment

1. Set up webhook endpoints in your email service
2. Configure email service to POST to `/api/v1/webhook/email`
3. Test the full workflow end-to-end
4. Monitor LangSmith traces for debugging
5. Set up alerts for errors and high latency
