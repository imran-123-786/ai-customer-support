-- SupportAgent AI Schema --
-- Complete persistence for conversations, memory, tools, tickets, and mock enterprise data --

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'customer',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    preferred_language TEXT DEFAULT 'auto',
    voice_enabled INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    tier TEXT DEFAULT 'Standard',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT NOT NULL, -- 'pending', 'processing', 'shipped', 'delivered', 'cancelled'
    delivery_address TEXT,
    tracking_number TEXT,
    order_date TEXT DEFAULT CURRENT_TIMESTAMP,
    delivered_date TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    method TEXT DEFAULT 'credit_card',
    status TEXT NOT NULL, -- 'captured', 'failed', 'refunded', 'duplicate_flagged'
    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT,
    status TEXT NOT NULL, -- 'requested', 'approved', 'rejected', 'processed'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(order_id),
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    customer_id TEXT,
    topic TEXT NOT NULL,
    intent TEXT NOT NULL,
    priority TEXT NOT NULL, -- 'Low', 'Medium', 'High', 'Critical'
    status TEXT DEFAULT 'Open', -- 'Open', 'In Progress', 'Waiting', 'Resolved', 'Closed'
    escalated INTEGER DEFAULT 0,
    escalation_reason TEXT,
    handoff_summary TEXT,
    assigned_to TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS ticket_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'created', 'status_changed', 'escalated', 'note_added'
    details TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(ticket_id) REFERENCES tickets(id)
);

CREATE TABLE IF NOT EXISTS customer_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    memory_type TEXT NOT NULL, -- 'preference', 'language_preference', 'style_preference', 'known_issue', 'account_context'
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, memory_type, memory_key)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    customer_id TEXT,
    title TEXT,
    summary TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system', 'tool'
    content TEXT NOT NULL,
    intent TEXT,
    emotion TEXT,
    confidence REAL,
    sources_json TEXT,
    tool_calls_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT,
    uploaded_by INTEGER,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    chunk_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    section TEXT,
    metadata_json TEXT,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    tool_name TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    latency_ms REAL,
    success INTEGER DEFAULT 1,
    error_message TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    customer_id TEXT,
    user_message TEXT,
    intent TEXT,
    emotion TEXT,
    priority TEXT,
    steps_count INTEGER DEFAULT 0,
    tools_called_count INTEGER DEFAULT 0,
    retrieval_count INTEGER DEFAULT 0,
    start_time TEXT,
    end_time TEXT,
    latency_ms REAL,
    final_action TEXT,
    escalated INTEGER DEFAULT 0,
    escalation_reason TEXT,
    failure_category TEXT, -- 'MODEL_FAILURE', 'RETRIEVAL_FAILURE', 'TOOL_FAILURE', 'PARSING_FAILURE', etc.
    success INTEGER DEFAULT 1,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    eval_name TEXT NOT NULL,
    total_cases INTEGER NOT NULL,
    passed_cases INTEGER NOT NULL,
    accuracy_score REAL NOT NULL,
    metrics_json TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    message_id INTEGER,
    csat_score INTEGER NOT NULL, -- 1 to 5
    feedback_text TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Legacy compatibility table view/table for older 'chats' queries
CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_message TEXT,
    bot_reply TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
