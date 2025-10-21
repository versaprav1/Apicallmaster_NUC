"""
langchain_db_query.py

A function-based module to query a PostgreSQL database using natural language via LangChain, supporting both SQLAlchemy and psycopg2, and both OpenAI and Ollama LLMs.
"""

import os
from typing import List, Optional, Any, Dict

# Database imports
import psycopg2
from sqlalchemy import create_engine, text

# LangChain imports
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import OpenAI, Ollama
from langchain.chains import create_sql_query_chain

# Load environment variables (optional)
from dotenv import load_dotenv
load_dotenv()

# --- Database Connection Functions ---
def get_sqlalchemy_engine() -> Any:
    """Create a SQLAlchemy engine from environment variables."""
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL not set in environment.")
    return create_engine(db_url)

def get_psycopg2_conn() -> Any:
    """Create a psycopg2 connection from environment variables."""
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432)
    )

# --- LLM Setup Functions ---
def get_openai_llm() -> Any:
    """Return an OpenAI LLM instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment.")
    return OpenAI(openai_api_key=api_key, temperature=0)

def get_ollama_llm(model: str = "llama3") -> Any:
    """Return an Ollama LLM instance (local)."""
    return Ollama(model=model)

# --- Schema Introspection & Table Selection ---
def get_sql_database(connection_string: str) -> SQLDatabase:
    """Create a LangChain SQLDatabase object for schema introspection."""
    return SQLDatabase.from_uri(connection_string)

def get_relevant_tables(sql_db: SQLDatabase, question: str) -> List[str]:
    """Return a list of relevant tables for the question (simple keyword match)."""
    # For large schemas, implement a smarter selection (e.g., embeddings)
    all_tables = sql_db.get_usable_table_names()
    relevant = [t for t in all_tables if any(word in t for word in question.lower().split())]
    return relevant if relevant else all_tables[:5]  # fallback: first 5 tables

# --- Query Generation and Execution ---
def generate_sql_query(llm: Any, sql_db: SQLDatabase, question: str, tables: Optional[List[str]] = None) -> str:
    """Generate a SQL query from a natural language question using the LLM."""
    chain = create_sql_query_chain(llm, sql_db)
    if tables:
        sql_db.table_info = {t: sql_db.table_info[t] for t in tables if t in sql_db.table_info}
    return chain.invoke({"question": question})

def execute_sqlalchemy_query(engine: Any, sql: str) -> List[Dict[str, Any]]:
    """Execute a SQL query using SQLAlchemy and return results as list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result.fetchall()]

def execute_psycopg2_query(conn: Any, sql: str) -> List[Dict[str, Any]]:
    """Execute a SQL query using psycopg2 and return results as list of dicts."""
    with conn.cursor() as cur:
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

# --- Main Query Function ---
def query_db_nl(
    question: str,
    llm_type: str = "openai",  # or "ollama"
    db_method: str = "sqlalchemy",  # or "psycopg2"
    ollama_model: str = "llama3"
) -> List[Dict[str, Any]]:
    """Main function: answer a natural language question using the selected LLM and DB method."""
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
        conn_str = os.getenv("DB_URL")
    elif db_method == "psycopg2":
        conn = get_psycopg2_conn()
        # Build SQLAlchemy-style URI for schema introspection
        conn_str = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', 5432)}/{os.getenv('DB_NAME')}"
    else:
        raise ValueError("db_method must be 'sqlalchemy' or 'psycopg2'")

    # Schema introspection
    sql_db = get_sql_database(conn_str)
    tables = get_relevant_tables(sql_db, question)

    # Generate SQL
    sql = generate_sql_query(llm, sql_db, question, tables)

    # Execute SQL
    if db_method == "sqlalchemy":
        return execute_sqlalchemy_query(engine, sql)
    else:
        return execute_psycopg2_query(conn, sql)
