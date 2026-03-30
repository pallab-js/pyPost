import pytest
import tempfile
import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import (
    StructuredLogger,
    LogEntry,
    RequestLog,
    LogLevel,
    RequestPhase,
    get_logger,
    set_request_context,
    clear_request_context,
)


class TestLogEntry:
    def test_log_entry_creation(self):
        entry = LogEntry(
            level=LogLevel.INFO.value,
            phase=RequestPhase.SENDING.value,
            message="Test message",
        )
        assert entry.level == LogLevel.INFO.value
        assert entry.phase == RequestPhase.SENDING.value
        assert entry.message == "Test message"
        assert entry.id is not None
        assert entry.timestamp is not None

    def test_log_entry_to_dict(self):
        entry = LogEntry(
            level=LogLevel.ERROR.value,
            phase=RequestPhase.FAILED.value,
            message="Error occurred",
            request_id="req-123",
        )
        d = entry.to_dict()
        assert d["level"] == LogLevel.ERROR.value
        assert d["request_id"] == "req-123"

    def test_log_entry_to_json(self):
        entry = LogEntry(message="Test")
        json_str = entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["message"] == "Test"


class TestRequestLog:
    def test_request_log_creation(self):
        log = RequestLog(
            request_id="req-456",
            collection_id="col-123",
            request_name="Get Users",
            url="https://api.example.com/users",
            method="GET",
            request_headers={"Authorization": "Bearer token"},
            request_body=None,
            request_params={},
        )
        assert log.request_id == "req-456"
        assert log.request_name == "Get Users"
        assert log.response_status is None

    def test_request_log_to_dict(self):
        log = RequestLog(
            request_id="req-789",
            collection_id="col-001",
            request_name="Create User",
            url="https://api.example.com/users",
            method="POST",
            request_headers={},
            request_body={"name": "John"},
            request_params={},
        )
        d = log.to_dict()
        assert d["request_id"] == "req-789"
        assert d["response_status"] is None


class TestStructuredLogger:
    def test_logger_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            assert logger._log_dir == Path(tmpdir)
            assert logger._db_path.exists()

    def test_log_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)
            logger.log(
                "Test log message",
                level=LogLevel.INFO,
                phase=RequestPhase.SENDING,
            )
            time.sleep(0.5)
            logger.stop()

    def test_log_request_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)
            logger.log_request_start(
                request_id="req-001",
                request_name="Test Request",
                url="https://api.example.com",
                method="GET",
            )
            time.sleep(0.5)
            logger.stop()

    def test_log_request_complete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)
            logger.log_request_complete(
                request_id="req-002",
                status_code=200,
                elapsed_ms=150.5,
            )
            time.sleep(0.5)
            logger.stop()

    def test_log_assertions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)
            assertions = [
                {"name": "Status Code", "passed": True},
                {"name": "Response Body", "passed": False},
            ]
            logger.log_assertions("req-003", assertions)
            time.sleep(0.5)
            logger.stop()

    def test_save_and_get_request_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)

            log = RequestLog(
                request_id="req-004",
                collection_id="col-001",
                request_name="Test",
                url="https://api.example.com",
                method="GET",
                request_headers={},
                request_body=None,
                request_params={},
                response_status=200,
                response_time_ms=100.0,
            )
            logger.save_request_log(log)

            retrieved = logger.get_request_log("req-004")
            assert retrieved is not None
            assert retrieved.request_id == "req-004"
            assert retrieved.response_status == 200

            logger.stop()

    def test_get_request_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)

            for i in range(3):
                log = RequestLog(
                    request_id=f"req-00{i}",
                    collection_id="col-001",
                    request_name=f"Request {i}",
                    url="https://api.example.com",
                    method="GET",
                    request_headers={},
                    request_body=None,
                    request_params={},
                )
                logger.save_request_log(log)

            logs = logger.get_request_logs(limit=10)
            assert len(logs) >= 3

            logger.stop()

    def test_get_request_logs_by_collection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)

            for col_id in ["col-A", "col-B"]:
                for i in range(2):
                    log = RequestLog(
                        request_id=f"req-{col_id}-{i}",
                        collection_id=col_id,
                        request_name=f"Request {i}",
                        url="https://api.example.com",
                        method="GET",
                        request_headers={},
                        request_body=None,
                        request_params={},
                    )
                    logger.save_request_log(log)

            logs_a = logger.get_request_logs(collection_id="col-A")
            assert all(log.collection_id == "col-A" for log in logs_a)

            logger.stop()

    def test_export_logs_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)

            log = RequestLog(
                request_id="req-export",
                collection_id="col-001",
                request_name="Export Test",
                url="https://api.example.com",
                method="GET",
                request_headers={},
                request_body=None,
                request_params={},
            )
            logger.save_request_log(log)
            time.sleep(0.5)

            output_path = Path(tmpdir) / "export.json"
            result = logger.export_logs(format="json", output_path=str(output_path))
            assert output_path.exists()

            content = output_path.read_text()
            data = json.loads(content)
            assert isinstance(data, list)
            assert len(data) >= 1

            logger.stop()

    def test_export_logs_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)

            log = RequestLog(
                request_id="req-csv",
                collection_id="col-001",
                request_name="CSV Test",
                url="https://api.example.com",
                method="GET",
                request_headers={},
                request_body=None,
                request_params={},
            )
            logger.save_request_log(log)
            time.sleep(0.5)

            output_path = Path(tmpdir) / "export.csv"
            result = logger.export_logs(format="csv", output_path=str(output_path))
            assert output_path.exists()

            content = output_path.read_text()
            lines = content.strip().split("\n")
            assert len(lines) >= 2
            assert "request_id" in lines[0]

            logger.stop()

    def test_log_user_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(log_dir=tmpdir)
            logger.start()
            time.sleep(0.5)
            logger.log_user_action(
                request_id="req-005",
                action="send_request",
                details={"method": "GET"},
            )
            time.sleep(0.5)
            logger.stop()


class TestLogLevels:
    def test_log_levels(self):
        assert LogLevel.DEBUG.value == 10
        assert LogLevel.INFO.value == 20
        assert LogLevel.WARNING.value == 30
        assert LogLevel.ERROR.value == 40
        assert LogLevel.CRITICAL.value == 50


class TestRequestPhases:
    def test_request_phases(self):
        assert RequestPhase.SENDING.value == "sending"
        assert RequestPhase.RESPONSE_RECEIVED.value == "response_received"
        assert RequestPhase.ASSERTIONS_RUN.value == "assertions_run"
        assert RequestPhase.CHAINING_APPLIED.value == "chaining_applied"
        assert RequestPhase.COMPLETED.value == "completed"
        assert RequestPhase.FAILED.value == "failed"


class TestRequestContextVar:
    def test_set_and_clear_request_context(self):
        set_request_context("req-123", "col-456")
        from core.logger import request_context_var
        ctx = request_context_var.get()
        assert ctx is not None
        assert ctx["request_id"] == "req-123"
        assert ctx["collection_id"] == "col-456"

        clear_request_context()
        assert request_context_var.get() is None
