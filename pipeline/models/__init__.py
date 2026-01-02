"""
Pipeline models package
"""
# Lazy import for sql_generator to avoid requiring torch/peft in production
try:
    from .sql_generator import SQLGenerator, create_sql_generator
    TINYLLAMA_AVAILABLE = True
except ImportError:
    SQLGenerator = None
    create_sql_generator = None
    TINYLLAMA_AVAILABLE = False

from .groq_client import GroqClient, create_groq_client

__all__ = [
    "SQLGenerator",
    "create_sql_generator",
    "GroqClient",
    "create_groq_client",
    "TINYLLAMA_AVAILABLE"
]
