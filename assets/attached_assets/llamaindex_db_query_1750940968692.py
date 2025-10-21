"""
llamaindex_db_query.py

A function-based module to query a PostgreSQL database using natural language via LlamaIndex, supporting both SQLAlchemy and psycopg2, and both OpenAI and Ollama LLMs.
"""

import os
from typing import List, Optional, Any, Dict

# Database imports
import psycopg2
from sqlalchemy import create_engine, text

# LlamaIndex imports
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.llms.ollama import Ollama as LlamaOllama

# Load environment variables (optional)
from dotenv import load_dotenv
load_dotenv()

# --- Database Connection Functions ---
def get_sqlalchemy_engine() -> Any:
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL not set in environment.")
    return create_engine(db_url)

def get_psycopg2_conn() -> Any:
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432)
    )

# --- LLM Setup Functions ---
def get_openai_llm() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment.")
    return LlamaOpenAI(api_key=api_key, temperature=0)

def get_ollama_llm(model: str = "llama3") -> Any:
    return LlamaOllama(model=model)

# --- Schema Introspection & Table Selection ---
def get_llamaindex_sql_database(engine: Any) -> SQLDatabase:
    return SQLDatabase(engine)

def get_relevant_tables(sql_db: SQLDatabase, question: str) -> List[str]:
    all_tables = sql_db.get_table_names()
    relevant = [t for t in all_tables if any(word in t for word in question.lower().split())]
    return relevant if relevant else all_tables[:5]

# --- Query Generation and Execution ---
def generate_sql_query(llm: Any, sql_db: SQLDatabase, question: str, tables: Optional[List[str]] = None) -> str:
    query_engine = NLSQLTableQueryEngine(
        sql_database=sql_db,
        llm=llm,
        table_names_to_use=tables
    )
    response = query_engine.query(question)
    return response.response if hasattr(response, 'response') else str(response)

def execute_sqlalchemy_query(engine: Any, sql: str) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]

def execute_psycopg2_query(conn: Any, sql: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

# --- Main Query Function ---
def query_db_nl_llamaindex(
    question: str,
    llm_type: str = "openai",  # or "ollama"
    db_method: str = "sqlalchemy",  # or "psycopg2"
    ollama_model: str = "llama3"
) -> Any:
    """Main function: answer a natural language question using the selected LLM and DB method (LlamaIndex)."""
    # Setup LLM
    if llm_type == "openai":
        llm = get_openai_llm()
    elif llm_type == "ollama":
        llm = get_ollama_llm(ollama_model)
    else:
        raise ValueError("llm_type must be 'openai' or 'ollama'")

    # Setup DB
    if db_method == "sqlalchemy":
        engine = get_sqlalchemy_engine()
        sql_db = get_llamaindex_sql_database(engine)
    elif db_method == "psycopg2":
        conn = get_psycopg2_conn()
        # For LlamaIndex, SQLAlchemy engine is preferred for schema introspection
        # So we create a temporary engine for schema, but use psycopg2 for execution
        db_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
        engine = create_engine(db_url)
        sql_db = get_llamaindex_sql_database(engine)
    else:
        raise ValueError("db_method must be 'sqlalchemy' or 'psycopg2'")

    # Table selection
    tables = get_relevant_tables(sql_db, question)

    # Generate SQL and get answer
    answer = generate_sql_query(llm, sql_db, question, tables)
    return answer
