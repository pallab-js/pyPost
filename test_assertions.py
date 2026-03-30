import pytest
from core.assertions import (
    AssertionEngine, AssertionResult, AssertionOperator,
    StatusCodeAssertion, JSONPathAssertion, HeaderAssertion,
    ResponseTimeAssertion, BodyContainsAssertion
)


class TestStatusCodeAssertion:
    def test_equals_pass(self):
        assertion = StatusCodeAssertion("Test", AssertionOperator.EQUALS, 200)
        result = assertion.evaluate({'status_code': 200})
        assert result.passed is True

    def test_equals_fail(self):
        assertion = StatusCodeAssertion("Test", AssertionOperator.EQUALS, 200)
        result = assertion.evaluate({'status_code': 404})
        assert result.passed is False

    def test_in_pass(self):
        assertion = StatusCodeAssertion("Test", AssertionOperator.IN, [200, 201, 202])
        result = assertion.evaluate({'status_code': 201})
        assert result.passed is True

    def test_less_than_pass(self):
        assertion = StatusCodeAssertion("Test", AssertionOperator.LESS_THAN, 300)
        result = assertion.evaluate({'status_code': 200})
        assert result.passed is True


class TestJSONPathAssertion:
    def test_simple_path(self):
        assertion = JSONPathAssertion("Test", "data.name", AssertionOperator.EQUALS, "John")
        result = assertion.evaluate({'text': '{"data": {"name": "John"}}'})
        assert result.passed is True
        assert result.actual == "John"

    def test_array_index(self):
        assertion = JSONPathAssertion("Test", "users.0.name", AssertionOperator.EXISTS)
        result = assertion.evaluate({'text': '{"users": [{"name": "Alice"}]}'})
        assert result.passed is True

    def test_contains(self):
        assertion = JSONPathAssertion("Test", "message", AssertionOperator.CONTAINS, "error")
        result = assertion.evaluate({'text': '{"message": "error occurred"}'})
        assert result.passed is True

    def test_not_exists(self):
        assertion = JSONPathAssertion("Test", "missing", AssertionOperator.NOT_EXISTS)
        result = assertion.evaluate({'text': '{"data": {}}'})
        assert result.passed is True


class TestHeaderAssertion:
    def test_header_equals_pass(self):
        assertion = HeaderAssertion("Test", "Content-Type", AssertionOperator.EQUALS, "application/json")
        result = assertion.evaluate({'headers': {'Content-Type': 'application/json'}})
        assert result.passed is True

    def test_header_exists_pass(self):
        assertion = HeaderAssertion("Test", "X-Request-Id", AssertionOperator.EXISTS)
        result = assertion.evaluate({'headers': {'X-Request-Id': '123'}})
        assert result.passed is True

    def test_header_not_exists(self):
        assertion = HeaderAssertion("Test", "X-Missing", AssertionOperator.NOT_EXISTS)
        result = assertion.evaluate({'headers': {}})
        assert result.passed is True


class TestResponseTimeAssertion:
    def test_less_than_pass(self):
        assertion = ResponseTimeAssertion("Test", AssertionOperator.LESS_THAN, 500)
        result = assertion.evaluate({'response_time': 200})
        assert result.passed is True

    def test_less_than_fail(self):
        assertion = ResponseTimeAssertion("Test", AssertionOperator.LESS_THAN, 500)
        result = assertion.evaluate({'response_time': 600})
        assert result.passed is False


class TestBodyContainsAssertion:
    def test_contains_pass(self):
        assertion = BodyContainsAssertion("Test", AssertionOperator.CONTAINS, "success")
        result = assertion.evaluate({'text': '{"status": "success"}'})
        assert result.passed is True

    def test_not_contains_pass(self):
        assertion = BodyContainsAssertion("Test", AssertionOperator.NOT_CONTAINS, "error")
        result = assertion.evaluate({'text': '{"status": "success"}'})
        assert result.passed is True

    def test_matches_regex(self):
        assertion = BodyContainsAssertion("Test", AssertionOperator.MATCHES, r"\d{3}-\d{4}")
        result = assertion.evaluate({'text': 'Phone: 123-4567'})
        assert result.passed is True


class TestAssertionEngine:
    def test_add_status_code_assertion(self):
        engine = AssertionEngine()
        result = engine.add({
            'type': 'status_code',
            'name': 'Test',
            'operator': 'equals',
            'expected': 200
        })
        assert result is True
        assert engine.count == 1

    def test_add_json_path_assertion(self):
        engine = AssertionEngine()
        result = engine.add({
            'type': 'json_path',
            'name': 'Test',
            'path': 'data.id',
            'operator': 'equals',
            'expected': 123
        })
        assert result is True

    def test_run_assertions(self):
        engine = AssertionEngine()
        engine.add({
            'type': 'status_code',
            'name': 'Status',
            'operator': 'equals',
            'expected': 200
        })
        engine.add({
            'type': 'response_time',
            'name': 'Speed',
            'operator': 'less_than',
            'expected': 500
        })
        
        response = {'status_code': 200, 'response_time': 100}
        results = engine.run(response)
        
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_summary(self):
        engine = AssertionEngine()
        engine.add({
            'type': 'status_code',
            'name': 'Test',
            'operator': 'equals',
            'expected': 200
        })
        
        results = engine.run({'status_code': 200})
        summary = engine.summary(results)
        
        assert summary['total'] == 1
        assert summary['passed'] == 1
        assert summary['failed'] == 0

    def test_invalid_assertion_type(self):
        engine = AssertionEngine()
        result = engine.add({
            'type': 'invalid_type',
            'name': 'Test'
        })
        assert result is False
