import json
import logging
import logging.handlers
import sqlite3
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor


request_context_var: ContextVar[Optional[Dict[str, str]]] = ContextVar(
    "request_context", default=None
)


class LogLevel(Enum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class RequestPhase(Enum):
    SENDING = "sending"
    RESPONSE_RECEIVED = "response_received"
    ASSERTIONS_RUN = "assertions_run"
    CHAINING_APPLIED = "chaining_applied"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LogEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    level: str = LogLevel.INFO.value
    phase: str = RequestPhase.SENDING.value
    request_id: Optional[str] = None
    collection_id: Optional[str] = None
    request_name: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    elapsed_ms: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    user_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class RequestLog:
    request_id: str
    collection_id: Optional[str]
    request_name: str
    url: str
    method: str
    request_headers: Dict[str, str]
    request_body: Any
    request_params: Dict[str, str]
    response_status: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[Any] = None
    response_time_ms: Optional[float] = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    chain_results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StructuredLogger:
    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_file_size_mb: int = 100,
        max_files: int = 10,
        retention_days: int = 30,
    ):
        self._log_dir = Path(log_dir or self._get_default_log_dir())
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._max_files = max_files
        self._retention_days = retention_days
        self._lock = threading.Lock()
        self._queue: Queue = Queue(maxsize=10000)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="logger")
        self._running = False
        self._db_path = self._log_dir / "request_logs.db"
        self._init_database()
        self._setup_file_handler()

    def _get_default_log_dir(self) -> str:
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS).parent
        else:
            base = Path(__file__).parent.parent
        return str(base / "logs")

    def _init_database(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    id TEXT PRIMARY KEY,
                    request_id TEXT,
                    collection_id TEXT,
                    request_name TEXT,
                    url TEXT,
                    method TEXT,
                    request_headers TEXT,
                    request_body TEXT,
                    request_params TEXT,
                    response_status INTEGER,
                    response_headers TEXT,
                    response_body TEXT,
                    response_time_ms REAL,
                    assertions TEXT,
                    chain_results TEXT,
                    errors TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_logs_request_id 
                ON request_logs(request_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_logs_collection_id 
                ON request_logs(collection_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_logs_timestamp 
                ON request_logs(started_at)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    level INTEGER,
                    phase TEXT,
                    request_id TEXT,
                    collection_id TEXT,
                    request_name TEXT,
                    url TEXT,
                    method TEXT,
                    status_code INTEGER,
                    elapsed_ms REAL,
                    message TEXT,
                    details TEXT,
                    user_action TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _setup_file_handler(self) -> None:
        self._file_handler = logging.handlers.RotatingFileHandler(
            self._log_dir / "app.log",
            maxBytes=self._max_file_size,
            backupCount=self._max_files,
        )
        self._file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    def start(self) -> None:
        self._running = True
        self._executor.submit(self._process_queue)
        self._executor.submit(self._cleanup_old_logs)

    def stop(self) -> None:
        self._running = False
        self._queue.join()
        self._executor.shutdown(wait=True)

    def _process_queue(self) -> None:
        while self._running:
            try:
                entry = self._queue.get(timeout=1.0)
                self._write_entry(entry)
                self._queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing log entry: {e}")

    def _write_entry(self, entry: LogEntry) -> None:
        try:
            with open(self._log_dir / "structured.log", "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception:
            pass

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO log_entries (
                        id, timestamp, level, phase, request_id, collection_id,
                        request_name, url, method, status_code, elapsed_ms,
                        message, details, user_action
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.id,
                        entry.timestamp,
                        entry.level,
                        entry.phase,
                        entry.request_id,
                        entry.collection_id,
                        entry.request_name,
                        entry.url,
                        entry.method,
                        entry.status_code,
                        entry.elapsed_ms,
                        entry.message,
                        json.dumps(entry.details),
                        entry.user_action,
                    ),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Failed to write to database: {e}")

    def _cleanup_old_logs(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "DELETE FROM log_entries WHERE timestamp < ?",
                    (cutoff.isoformat(),),
                )
                conn.execute(
                    "DELETE FROM request_logs WHERE started_at < ?",
                    (cutoff.isoformat(),),
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {e}")

    def log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        phase: RequestPhase = RequestPhase.SENDING,
        **kwargs,
    ) -> None:
        entry = LogEntry(
            level=level.value,
            phase=phase.value,
            message=message,
            **kwargs,
        )
        try:
            self._queue.put_nowait(entry)
        except Exception:
            pass

    def log_request_start(
        self,
        request_id: str,
        request_name: str,
        url: str,
        method: str,
        collection_id: Optional[str] = None,
    ) -> None:
        self.log(
            f"Starting request: {request_name}",
            phase=RequestPhase.SENDING,
            request_id=request_id,
            collection_id=collection_id,
            request_name=request_name,
            url=url,
            method=method,
        )

    def log_request_complete(
        self,
        request_id: str,
        status_code: int,
        elapsed_ms: float,
        errors: Optional[List[str]] = None,
    ) -> None:
        phase = RequestPhase.COMPLETED if status_code < 400 else RequestPhase.FAILED
        self.log(
            f"Request completed with status {status_code}",
            level=LogLevel.ERROR if errors else LogLevel.INFO,
            phase=phase,
            request_id=request_id,
            status_code=status_code,
            elapsed_ms=elapsed_ms,
            details={"errors": errors or []},
        )

    def log_assertions(
        self,
        request_id: str,
        assertions: List[Dict[str, Any]],
    ) -> None:
        passed = sum(1 for a in assertions if a.get("passed"))
        failed = len(assertions) - passed
        self.log(
            f"Assertions: {passed} passed, {failed} failed",
            phase=RequestPhase.ASSERTIONS_RUN,
            request_id=request_id,
            details={"assertions": assertions},
        )

    def log_chain_result(
        self,
        request_id: str,
        chain_results: List[Dict[str, Any]],
    ) -> None:
        self.log(
            f"Chain extraction completed with {len(chain_results)} results",
            phase=RequestPhase.CHAINING_APPLIED,
            request_id=request_id,
            details={"chain_results": chain_results},
        )

    def log_user_action(
        self,
        request_id: Optional[str],
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.log(
            f"User action: {action}",
            user_action=action,
            request_id=request_id,
            details=details or {},
        )

    def save_request_log(self, log: RequestLog) -> None:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO request_logs (
                            id, request_id, collection_id, request_name, url,
                            method, request_headers, request_body, request_params,
                            response_status, response_headers, response_body,
                            response_time_ms, assertions, chain_results, errors,
                            started_at, completed_at, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            log.request_id,
                            log.request_id,
                            log.collection_id,
                            log.request_name,
                            log.url,
                            log.method,
                            json.dumps(log.request_headers),
                            json.dumps(log.request_body),
                            json.dumps(log.request_params),
                            log.response_status,
                            json.dumps(log.response_headers)
                            if log.response_headers
                            else None,
                            json.dumps(log.response_body) if log.response_body else None,
                            log.response_time_ms,
                            json.dumps(log.assertions),
                            json.dumps(log.chain_results),
                            json.dumps(log.errors),
                            log.started_at,
                            log.completed_at,
                            json.dumps(log.metadata),
                        ),
                    )
                    conn.commit()
            except Exception as e:
                logging.error(f"Failed to save request log: {e}")

    def get_request_logs(
        self,
        collection_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RequestLog]:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    query = "SELECT * FROM request_logs"
                    params = []
                    if collection_id:
                        query += " WHERE collection_id = ?"
                        params.append(collection_id)
                    query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    return [self._row_to_request_log(row) for row in rows]
            except Exception as e:
                logging.error(f"Failed to get request logs: {e}")
                return []

    def get_request_log(self, request_id: str) -> Optional[RequestLog]:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        "SELECT * FROM request_logs WHERE request_id = ?",
                        (request_id,),
                    )
                    row = cursor.fetchone()
                    return self._row_to_request_log(row) if row else None
            except Exception as e:
                logging.error(f"Failed to get request log: {e}")
                return None

    def _row_to_request_log(self, row: sqlite3.Row) -> RequestLog:
        return RequestLog(
            request_id=row["request_id"],
            collection_id=row["collection_id"],
            request_name=row["request_name"],
            url=row["url"],
            method=row["method"],
            request_headers=json.loads(row["request_headers"] or "{}"),
            request_body=json.loads(row["request_body"] or "null"),
            request_params=json.loads(row["request_params"] or "{}"),
            response_status=row["response_status"],
            response_headers=json.loads(row["response_headers"] or "null"),
            response_body=json.loads(row["response_body"] or "null"),
            response_time_ms=row["response_time_ms"],
            assertions=json.loads(row["assertions"] or "[]"),
            chain_results=json.loads(row["chain_results"] or "[]"),
            errors=json.loads(row["errors"] or "[]"),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def export_logs(
        self,
        format: str = "json",
        output_path: Optional[str] = None,
        collection_id: Optional[str] = None,
    ) -> str:
        logs = self.get_request_logs(collection_id=collection_id, limit=10000)
        if format == "json":
            content = json.dumps([log.to_dict() for log in logs], indent=2)
        elif format == "csv":
            if not logs:
                return ""
            headers = [
                "request_id",
                "request_name",
                "url",
                "method",
                "response_status",
                "response_time_ms",
            ]
            lines = [",".join(headers)]
            for log in logs:
                lines.append(
                    ",".join(
                        str(log.to_dict().get(h, ""))
                        for h in headers
                    )
                )
            content = "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

        if output_path:
            Path(output_path).write_text(content)
            return output_path
        return content


import sys

_global_logger: Optional[StructuredLogger] = None


def get_logger(name: Optional[str] = None) -> StructuredLogger:
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger()
    return _global_logger


def set_request_context(request_id: str, collection_id: Optional[str] = None) -> None:
    request_context_var.set(
        {"request_id": request_id, "collection_id": collection_id}
    )


def clear_request_context() -> None:
    request_context_var.set(None)
