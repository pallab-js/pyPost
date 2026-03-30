import pytest
import tempfile
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.audit import (
    AuditLogger,
    AuditEntry,
    AuditReport,
    AuditEventType,
    AuditSeverity,
    get_audit_logger,
)


class TestAuditEntry:
    def test_entry_creation(self):
        entry = AuditEntry(
            id="test-123",
            timestamp="2024-01-01T00:00:00Z",
            event_type="request_sent",
            severity="info",
            user_id="user-1",
            session_id="session-1",
            details={"url": "https://api.example.com"},
        )
        assert entry.id == "test-123"
        assert entry.event_type == "request_sent"
        assert entry.severity == "info"

    def test_entry_to_dict(self):
        entry = AuditEntry(
            id="test-456",
            timestamp="2024-01-01T00:00:00Z",
            event_type="error_occurred",
            severity="error",
            user_id=None,
            session_id="session-2",
            details={"error": "test error"},
        )
        d = entry.to_dict()
        assert d["id"] == "test-456"
        assert d["severity"] == "error"

    def test_entry_to_json(self):
        entry = AuditEntry(
            id="test-789",
            timestamp="2024-01-01T00:00:00Z",
            event_type="request_sent",
            severity="info",
            user_id=None,
            session_id=None,
            details={},
        )
        json_str = entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["id"] == "test-789"


class TestAuditLogger:
    def test_logger_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            assert logger._db_path == f"{tmpdir}/audit.db"

    def test_log_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            entry_id = logger.log(AuditEventType.REQUEST_SENT)
            assert entry_id is not None

    def test_log_request_sent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            entry_id = logger.log_request_sent(
                url="https://api.example.com",
                method="GET",
                status_code=200,
                duration_ms=150.5,
            )
            assert entry_id is not None

    def test_log_security_scan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            entry_id = logger.log_security_scan(
                url="https://api.example.com",
                findings_count=5,
                risk_score=25.0,
                critical_count=1,
                high_count=2,
            )
            assert entry_id is not None

    def test_log_collection_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            entry_id = logger.log_collection_run(
                collection_id="col-123",
                collection_name="Test Collection",
                total_requests=10,
                passed=8,
                failed=2,
                duration_ms=5000.0,
            )
            assert entry_id is not None

    def test_log_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            entry_id = logger.log_error(
                error_type="ConnectionError",
                error_message="Failed to connect",
                context={"url": "https://api.example.com"},
            )
            assert entry_id is not None

    def test_get_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.REQUEST_SAVED)
            entries = logger.get_entries()
            assert len(entries) >= 2

    def test_get_entries_with_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            for _ in range(5):
                logger.log(AuditEventType.REQUEST_SENT)
            entries = logger.get_entries(limit=3)
            assert len(entries) == 3

    def test_get_entries_by_event_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.COLLECTION_CREATED)
            entries = logger.get_entries(
                event_types=[AuditEventType.REQUEST_SENT]
            )
            assert all(e.event_type == "request_sent" for e in entries)

    def test_get_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.ERROR_OCCURRED)
            start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            end = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            report = logger.get_report(start_date=start, end_date=end)
            assert isinstance(report, AuditReport)
            assert report.summary.get("request_sent", 0) >= 2

    def test_get_event_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.REQUEST_SENT)
            logger.log(AuditEventType.COLLECTION_CREATED)
            counts = logger.get_event_counts(days=30)
            assert counts.get("request_sent", 0) >= 2

    def test_export_logs_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            output_path = f"{tmpdir}/export.json"
            result = logger.export_logs(format="json", output_path=output_path)
            assert Path(output_path).exists()
            with open(output_path) as f:
                data = json.load(f)
                assert isinstance(data, list)

    def test_export_logs_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            output_path = f"{tmpdir}/export.csv"
            result = logger.export_logs(format="csv", output_path=output_path)
            assert Path(output_path).exists()
            with open(output_path) as f:
                content = f.read()
                assert "id,timestamp" in content

    def test_clear_old_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.log(AuditEventType.REQUEST_SENT)
            deleted = logger.clear_old_entries(days=0)
            assert deleted >= 0

    def test_set_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            logger.set_user("test-user")
            assert logger._user_id == "test-user"

    def test_get_session_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger(db_path=f"{tmpdir}/audit.db")
            session_id = logger.get_session_id()
            assert session_id is not None
            assert len(session_id) == 36


class TestAuditEventType:
    def test_event_types_exist(self):
        assert AuditEventType.REQUEST_SENT.value == "request_sent"
        assert AuditEventType.REQUEST_SAVED.value == "request_saved"
        assert AuditEventType.SECURITY_SCAN_PERFORMED.value == "security_scan_performed"
        assert AuditEventType.ERROR_OCCURRED.value == "error_occurred"

    def test_all_event_types_defined(self):
        assert len(AuditEventType) > 20


class TestAuditSeverity:
    def test_severity_values(self):
        assert AuditSeverity.DEBUG.value == "debug"
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditReport:
    def test_report_creation(self):
        entries = [
            AuditEntry(
                id="1",
                timestamp="2024-01-01T00:00:00Z",
                event_type="request_sent",
                severity="info",
                user_id=None,
                session_id=None,
                details={},
            )
        ]
        report = AuditReport(
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-01-01T23:59:59Z",
            entries=entries,
            summary={"request_sent": 1},
            critical_events=[],
        )
        assert len(report.entries) == 1
        assert report.summary["request_sent"] == 1

    def test_report_to_dict(self):
        report = AuditReport(
            start_date="2024-01-01T00:00:00Z",
            end_date="2024-01-01T23:59:59Z",
            entries=[],
            summary={},
            critical_events=[],
        )
        d = report.to_dict()
        assert d["start_date"] == "2024-01-01T00:00:00Z"
        assert "entries" in d
