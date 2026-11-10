import mysql.connector
from mysql.connector import Error
from config import Config


def get_db_connection():
    """
    Establish and return a new MySQL connection using configuration settings.
    """
    try:
        connection = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
        )
        return connection
    except Error as e:
        # Re-raise with informative message for logging and debugging
        raise RuntimeError(f"Database connection error: {e}") from e


def query_db(query, args=(), one=False):
    """
    Execute a parameterized SELECT query and return rows as dictionaries.

    :param query: SQL query with %s placeholders
    :param args: tuple or list of parameters
    :param one: if True, returns a single dictionary or None; else a list of dictionaries
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, args)
        result = cursor.fetchall()
        return (result[0] if result else None) if one else result
    except Error as e:
        raise RuntimeError(f"Database query error: {e}") from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


def execute_db(query, args=(), commit=True):
    """
    Execute a parameterized INSERT, UPDATE, or DELETE query.

    :param query: SQL query with %s placeholders
    :param args: tuple or list of parameters
    :param commit: whether to commit the transaction
    :return: dict with 'lastrowid' and 'rowcount'
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, args)
        if commit:
            conn.commit()
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        return {"lastrowid": last_id, "rowcount": row_count}
    except Error as e:
        if conn is not None:
            conn.rollback()
        raise RuntimeError(f"Database execution error: {e}") from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


def check_db_connection():
    """
    Quickly verify database connectivity and check if the database is accessible.
    Returns (True, message) on success or (False, error_message) on failure.
    """
    try:
        conn = get_db_connection()
        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE(), VERSION()")
            db_name, version = cursor.fetchone()
            cursor.close()
            conn.close()
            return True, f"Connected to MySQL {version} (Database: {db_name})"
        return False, "Failed to connect to MySQL"
    except Exception as e:
        return False, str(e)
