import sqlite3
import os
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
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

        # Templates table for request templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                template_data TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cache table for response caching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL UNIQUE,
                response_data TEXT NOT NULL,
                headers TEXT,
                status_code INTEGER,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        # Create index on cache_key for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_key ON response_cache(cache_key)
        """)

        # Create default environment
        cursor.execute("SELECT COUNT(*) FROM environments")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO environments (name, is_active) VALUES ('Default', 1)")

        conn.commit()
        conn.close()

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logging.error(f"Encryption error: {str(e)}")
            raise Exception(f"Failed to encrypt data: {str(e)}")

    def decrypt(self, data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.fernet.decrypt(data.encode()).decode()
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            raise Exception(f"Failed to decrypt data: {str(e)}")

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
        except sqlite3.OperationalError as e:
            logging.error(f"Database operational error: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
        except sqlite3.IntegrityError as e:
            logging.error(f"Database integrity error: {str(e)}")
            raise Exception(f"Database integrity constraint violated: {str(e)}")
        except sqlite3.Error as e:
            logging.error(f"Database error: {str(e)}")
            raise Exception(f"Database error: {str(e)}")
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
        except sqlite3.OperationalError as e:
            logging.error(f"Database operational error: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
        except sqlite3.IntegrityError as e:
            logging.error(f"Database integrity error: {str(e)}")
            raise Exception(f"Database integrity constraint violated: {str(e)}")
        except sqlite3.Error as e:
            logging.error(f"Database update error: {str(e)}")
            raise Exception(f"Database update error: {str(e)}")
        finally:
            if conn:
                conn.close()

    def get_cache_key(self, method: str, url: str, headers: Dict, data: Optional[str]) -> str:
        """Generate a cache key for the request"""
        key_data = f"{method}:{url}:{str(sorted(headers.items()))}:{data or ''}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available and not expired"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get cache entry that's not expired
            cursor.execute("""
                SELECT * FROM response_cache
                WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY cached_at DESC LIMIT 1
            """, (cache_key,))

            row = cursor.fetchone()
            if row:
                return {
                    'status_code': row['status_code'],
                    'headers': row['headers'] if row['headers'] else '{}',
                    'response_data': row['response_data'],
                    'cached': True
                }
            return None
        except sqlite3.Error as e:
            logging.warning(f"Cache retrieval error: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    def cache_response(self, cache_key: str, response_data: Dict, ttl_seconds: int = 300):
        """Cache a response with optional TTL"""
        try:
            # Calculate expiration time
            expires_at = None
            if ttl_seconds > 0:
                expires_at = time.time() + ttl_seconds

            self.execute_update("""
                INSERT OR REPLACE INTO response_cache
                (cache_key, response_data, headers, status_code, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                cache_key,
                response_data.get('text', ''),
                str(response_data.get('headers', {})),
                response_data.get('status_code', 0),
                expires_at
            ))
        except Exception as e:
            logging.warning(f"Cache storage error: {str(e)}")

    def clear_expired_cache(self):
        """Clear expired cache entries"""
        try:
            self.execute_update("DELETE FROM response_cache WHERE expires_at <= datetime('now')")
        except Exception as e:
            logging.warning(f"Cache cleanup error: {str(e)}")