import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from threading import RLock


class AuditEventType(Enum):
    REQUEST_SENT = "request_sent"
    REQUEST_SAVED = "request_saved"
    REQUEST_DELETED = "request_deleted"
    COLLECTION_CREATED = "collection_created"
    COLLECTION_UPDATED = "collection_updated"
    COLLECTION_DELETED = "collection_deleted"
    ENVIRONMENT_CREATED = "environment_created"
    ENVIRONMENT_UPDATED = "environment_updated"
    ENVIRONMENT_DELETED = "environment_deleted"
    SETTINGS_CHANGED = "settings_changed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    SECURITY_SCAN_PERFORMED = "security_scan_performed"
    SECURITY_FINDING = "security_finding"
    PLUGIN_ENABLED = "plugin_enabled"
    PLUGIN_DISABLED = "plugin_disabled"
    PLUGIN_INSTALLED = "plugin_installed"
    PLUGIN_UNINSTALLED = "plugin_uninstalled"
    MOCK_SERVER_STARTED = "mock_server_started"
    MOCK_SERVER_STOPPED = "mock_server_stopped"
    COLLECTION_RUN_STARTED = "collection_run_started"
    COLLECTION_RUN_COMPLETED = "collection_run_completed"
    IMPORT_PERFORMED = "import_performed"
    EXPORT_PERFORMED = "export_performed"
    ERROR_OCCURRED = "error_occurred"


class AuditSeverity(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    id: str
    timestamp: str
    event_type: str
    severity: str
    user_id: Optional[str]
    session_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class AuditReport:
    start_date: str
    end_date: str
    entries: List[AuditEntry]
    summary: Dict[str, int]
    critical_events: List[AuditEntry]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "entries": [e.to_dict() for e in self.entries],
            "summary": self.summary,
            "critical_events": [e.to_dict() for e in self.critical_events],
        }


class AuditLogger:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or self._get_default_db_path()
        self._lock = RLock()
        self._session_id = str(uuid.uuid4())
        self._user_id: Optional[str] = None
        self._init_database()

    def _get_default_db_path(self) -> str:
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS).parent
        else:
            base = Path(__file__).parent.parent
        return str(base / "data" / "audit.db")

    def _init_database(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_event_type
                ON audit_log(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user_id
                ON audit_log(user_id)
            """)
            conn.commit()

    def set_user(self, user_id: Optional[str] = None) -> None:
        self._user_id = user_id

    def get_session_id(self) -> str:
        return self._session_id

    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type.value,
            severity=severity.value,
            user_id=self._user_id,
            session_id=self._session_id,
            details=details or {},
            **kwargs,
        )

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute(
                        """
                        INSERT INTO audit_log (
                            id, timestamp, event_type, severity,
                            user_id, session_id, details, ip_address, user_agent
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entry.id,
                            entry.timestamp,
                            entry.event_type,
                            entry.severity,
                            entry.user_id,
                            entry.session_id,
                            json.dumps(entry.details),
                            entry.ip_address,
                            entry.user_agent,
                        ),
                    )
                    conn.commit()
            except Exception:
                pass

        return entry.id

    def log_request_sent(
        self,
        url: str,
        method: str,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ) -> str:
        return self.log(
            AuditEventType.REQUEST_SENT,
            details={
                "url": url,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

    def log_security_scan(
        self,
        url: str,
        findings_count: int,
        risk_score: float,
        critical_count: int = 0,
        high_count: int = 0,
    ) -> str:
        severity = AuditSeverity.CRITICAL if critical_count > 0 else (
            AuditSeverity.WARNING if high_count > 0 else AuditSeverity.INFO
        )
        return self.log(
            AuditEventType.SECURITY_SCAN_PERFORMED,
            severity=severity,
            details={
                "url": url,
                "findings_count": findings_count,
                "risk_score": risk_score,
                "critical_count": critical_count,
                "high_count": high_count,
            },
        )

    def log_collection_run(
        self,
        collection_id: str,
        collection_name: str,
        total_requests: int,
        passed: int,
        failed: int,
        duration_ms: float,
    ) -> str:
        severity = AuditSeverity.ERROR if failed > 0 else AuditSeverity.INFO
        return self.log(
            AuditEventType.COLLECTION_RUN_COMPLETED,
            severity=severity,
            details={
                "collection_id": collection_id,
                "collection_name": collection_name,
                "total_requests": total_requests,
                "passed": passed,
                "failed": failed,
                "duration_ms": duration_ms,
            },
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.log(
            AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.ERROR,
            details={
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
            },
        )

    def log_import_export(
        self,
        operation: str,
        format: str,
        item_count: int,
        filename: Optional[str] = None,
    ) -> str:
        return self.log(
            AuditEventType.IMPORT_PERFORMED if operation == "import" else AuditEventType.EXPORT_PERFORMED,
            details={
                "format": format,
                "item_count": item_count,
                "filename": filename,
            },
        )

    def get_entries(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    query = "SELECT * FROM audit_log WHERE 1=1"
                    params: List[Any] = []

                    if start_date:
                        query += " AND timestamp >= ?"
                        params.append(start_date)
                    if end_date:
                        query += " AND timestamp <= ?"
                        params.append(end_date)
                    if event_types:
                        placeholders = ",".join("?" * len(event_types))
                        query += f" AND event_type IN ({placeholders})"
                        params.extend([e.value for e in event_types])
                    if user_id:
                        query += " AND user_id = ?"
                        params.append(user_id)

                    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                    params.extend([limit, offset])

                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    return [self._row_to_entry(row) for row in rows]
            except Exception:
                return []

    def _row_to_entry(self, row: sqlite3.Row) -> AuditEntry:
        return AuditEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            severity=row["severity"],
            user_id=row["user_id"],
            session_id=row["session_id"],
            details=json.loads(row["details"] or "{}"),
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
        )

    def get_report(
        self,
        start_date: str,
        end_date: str,
    ) -> AuditReport:
        entries = self.get_entries(
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )

        summary: Dict[str, int] = {}
        for entry in entries:
            summary[entry.event_type] = summary.get(entry.event_type, 0) + 1

        critical_events = [
            e for e in entries
            if e.severity in [AuditSeverity.ERROR.value, AuditSeverity.CRITICAL.value]
        ]

        return AuditReport(
            start_date=start_date,
            end_date=end_date,
            entries=entries,
            summary=summary,
            critical_events=critical_events,
        )

    def get_event_counts(
        self,
        days: int = 30,
    ) -> Dict[str, int]:
        from datetime import timedelta
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        """
                        SELECT event_type, COUNT(*) as count
                        FROM audit_log
                        WHERE timestamp >= ?
                        GROUP BY event_type
                        """,
                        (start_date,),
                    )
                    rows = cursor.fetchall()
                    return {row[0]: row[1] for row in rows}
            except Exception:
                return {}

    def clear_old_entries(self, days: int = 90) -> int:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._lock:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.execute(
                        "DELETE FROM audit_log WHERE timestamp < ?",
                        (cutoff,),
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception:
                return 0

    def export_logs(
        self,
        format: str = "json",
        output_path: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        entries = self.get_entries(
            start_date=start_date,
            end_date=end_date,
            limit=100000,
        )

        if format == "json":
            content = json.dumps([e.to_dict() for e in entries], indent=2)
        elif format == "csv":
            if not entries:
                return ""
            headers = ["id", "timestamp", "event_type", "severity", "user_id", "session_id"]
            lines = [",".join(headers)]
            for entry in entries:
                lines.append(
                    ",".join(str(entry.to_dict().get(h, "")) for h in headers)
                )
            content = "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

        if output_path:
            Path(output_path).write_text(content)
            return output_path
        return content


import sys

_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger
