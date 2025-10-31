import sqlite3
import os
import logging
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet


class DatabaseManager:
    """Manages SQLite database operations for pyPost"""

    def __init__(self, db_path: str = "pypost.db"):
        self.db_path = db_path
        self.encryption_key_path = os.path.join(os.path.dirname(self.db_path), '.encryption_key')
        self._init_encryption()
        self.init_database()

    def _init_encryption(self):
        """Initialize encryption key and Fernet instance"""
        if not os.path.exists(self.encryption_key_path):
            self.encryption_key = Fernet.generate_key()
            with open(self.encryption_key_path, 'wb') as f:
                f.write(self.encryption_key)
        else:
            with open(self.encryption_key_path, 'rb') as f:
                self.encryption_key = f.read()
        self.fernet = Fernet(self.encryption_key)

    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                is_folder BOOLEAN DEFAULT 0,
                request_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES collections (id)
            )
        """)

        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                request_data TEXT,
                response_data TEXT,
                status_code INTEGER,
                response_time INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Environments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Environment variables table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environment_variables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                environment_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                FOREIGN KEY (environment_id) REFERENCES environments (id)
            )
        """)

        # Settings table for application preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Create default environment
        cursor.execute("SELECT COUNT(*) FROM environments")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO environments (name, is_active) VALUES ('Default', 1)")

        conn.commit()
        conn.close()

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, data: str) -> str:
        """Decrypt sensitive data"""
        return self.fernet.decrypt(data.encode()).decode()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return results as list of dictionaries"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except sqlite3.Error as e:
            logging.error(f"Database query error: {str(e)}")
            raise Exception(f"Database query error: {str(e)}")
        finally:
            if conn:
                conn.close()

    def execute_update(self, query: str, params: tuple = ()) -> Optional[int]:
        """Execute an update query and return the last row ID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            last_id = cursor.lastrowid
            return last_id
        except sqlite3.Error as e:
            logging.error(f"Database update error: {str(e)}")
            raise Exception(f"Database update error: {str(e)}")
        finally:
            if conn:
                conn.close()