import os
import sys
import sqlite3
import re
import json
from typing import Optional
from langchain_core.tools import tool

# Ensure backend folder is in path for database import
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import db


import sqlglot
from sqlglot import exp


class DatabaseConnectionError(Exception):
    """Exception raised for structural database errors like database locked or connection failures."""
    pass


def validate_select_query_only(sql_query: str) -> bool:
    """
    Parses the SQL query using sqlglot to verify:
    1. It is a read-only SELECT query.
    2. It only targets the allowed 'products' table.
    """
    try:
        # Parse the SQL query into an AST
        try:
            expression = sqlglot.parse_one(sql_query, read="sqlite")
        except (TypeError, Exception):
            try:
                expression = sqlglot.parse_one(sql_query, dialect="sqlite")
            except (TypeError, Exception):
                expression = sqlglot.parse_one(sql_query)

        if expression is None:
            return False
        
        # Verify it contains a SELECT statement
        if not isinstance(expression, exp.Select) and not expression.find(exp.Select):
            return False
            
        # Verify it does not contain forbidden modification nodes
        forbidden_nodes = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create)
        if isinstance(expression, forbidden_nodes) or any(expression.find(n) for n in forbidden_nodes):
            return False

        # Verify all tables queried are in the allowed list (only 'products' table)
        tables = list(expression.find_all(exp.Table))
        if not tables:
            # Query without tables (e.g. SELECT 1) is allowed as read-only
            return True

        for table in tables:
            raw_name = ""
            if hasattr(table, "name"):
                name_attr = getattr(table, "name")
                raw_name = name_attr() if callable(name_attr) else name_attr
            if not raw_name and hasattr(table, "this"):
                this_attr = getattr(table, "this")
                if hasattr(this_attr, "name"):
                    raw_name = getattr(this_attr, "name")
                    if callable(raw_name):
                        raw_name = raw_name()
                elif hasattr(this_attr, "this"):
                    raw_name = getattr(this_attr, "this")
                else:
                    raw_name = str(this_attr)

            table_name = str(raw_name).strip('"\'`').lower()
            if table_name != "products":
                return False
                
        return True
    except Exception as e:
        import logging
        logging.getLogger("products_db").warning(f"validate_select_query_only failed: {str(e)} for query {sql_query}")
        return False


@tool
def query_products_sql(sql_query: str) -> str:
    """Executes a read-only SQL query on the 'products' table.

    The table schema is:
    - id (TEXT PRIMARY KEY): unique product variant identifier
    - category (TEXT): product category (e.g. 'flagship_edp_50ml', 'luxury_collaboration', 'perfume_oils_shots_khamrias', 'body_splash_mists')
    - name (TEXT): product display name
    - price (REAL): standard price in EGP
    - promo_price (REAL): promo price in EGP (may be NULL)
    - variant (TEXT): variant name (may be NULL)
    - stock_quantity (INTEGER): units in stock
    - is_available (BOOLEAN): 1 if stock_quantity > 0, else 0
    - description (TEXT): detailed description

    Use this tool to find:
    - in stock products (stock_quantity > 0)
    - out of stock products (stock_quantity = 0)
    - available products (is_available = 1)
    
    Only read-only SELECT queries are allowed.
    """
    # Safety Check: only allow SELECT queries on 'products' table using AST Parser
    if not validate_select_query_only(sql_query):
        return "Error: Only read-only SELECT queries targeting the 'products' table are permitted on the products database."

    try:
        conn = sqlite3.connect(db.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No matching products found."

        results = [dict(row) for row in rows]
        return json.dumps(results[:10])
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        # Structural errors bubble up to trigger immediate human escalation
        if "locked" in error_msg or "unable to open" in error_msg or "no such table" in error_msg:
            raise DatabaseConnectionError(f"Database connection or locking issue: {str(e)}") from e
        # Semantic/syntax errors are returned to the LLM for self-correction
        return f"SQL Syntax Error: {str(e)}. Please correct your query and try again."
    except sqlite3.Error as e:
        # Other SQLite errors (corrupt database, database error, etc.) are structural
        raise DatabaseConnectionError(f"Database structural error: {str(e)}") from e
    except Exception as e:
        if isinstance(e, DatabaseConnectionError):
            raise
        return f"SQL Execution Error: {str(e)}"


@tool
def get_product_details(name: str, variant: Optional[str] = None) -> str:
    """Retrieves detailed information about a specific product and/or variant from the products database.

    Args:
        name: The name of the product (e.g. 'Flagship Eau de Parfum', 'Avec Hatshepsut', 'Vanilla Shot', 'Soft Cloud Heart')
        variant: Optional variant name (e.g. 'Rum', 'Dulce de Leche') for flagship perfumes.
    """
    try:
        conn = sqlite3.connect(db.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if variant:
            cursor.execute(
                "SELECT * FROM products WHERE (name LIKE ? OR category = ?) AND variant LIKE ?",
                (f"%{name}%", name, f"%{variant}%")
            )
        else:
            cursor.execute(
                "SELECT * FROM products WHERE name LIKE ? OR category = ?",
                (f"%{name}%", name)
            )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"No product details found matching name '{name}'" + (f" and variant '{variant}'" if variant else "")

        results = [dict(row) for row in rows]
        return json.dumps(results[:5])
    except Exception as e:
        return f"Error retrieving product details: {str(e)}"


@tool
def search_products_by_description(description_query: str, limit: int = 3) -> str:
    """Searches the products database semantically by product description.

    Use this when the customer asks for a fragrance based on notes, moods, ingredients, or descriptors (e.g. 'woody', 'sweet vanilla', 'warm spicy', 'refreshing fresh').

    Args:
        description_query: The text query describing fragrance notes or characteristics.
        limit: Max number of top relevant matches to return (default 3, max 5).
    """
    try:
        max_limit = min(max(1, limit), 5)
        results = db.semantic_search_products(description_query, limit=max_limit)
        if not results:
            return f"No products found matching description query: '{description_query}'"
        return json.dumps(results)
    except Exception as e:
        return f"Error performing semantic search: {str(e)}"
