import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class AssertionOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    NOT = "not"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MATCHES = "matches"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUALS = "less_than_or_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    IN = "in"
    NOT_IN = "not_in"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    HAS_KEY = "has_key"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IS_TYPE = "is_type"


@dataclass
class AssertionResult:
    name: str
    passed: bool
    expected: Any
    actual: Any
    message: str
    assertion_type: str
    details: Optional[str] = None


class BaseAssertion(ABC):
    def __init__(self, name: str, operator: AssertionOperator, expected: Any = None):
        self.name = name
        self.operator = operator
        self.expected = expected

    @abstractmethod
    def evaluate(self, response: Dict) -> AssertionResult:
        pass

    def _format_value(self, value: Any) -> str:
        if isinstance(value, dict):
            return json.dumps(value, indent=2)
        elif isinstance(value, list):
            return json.dumps(value)
        return str(value)


class StatusCodeAssertion(BaseAssertion):
    def evaluate(self, response: Dict) -> AssertionResult:
        actual = response.get('status_code', 0)
        
        if self.operator == AssertionOperator.EQUALS:
            passed = actual == self.expected
        elif self.operator == AssertionOperator.NOT_EQUALS:
            passed = actual != self.expected
        elif self.operator == AssertionOperator.IN:
            passed = actual in (self.expected if isinstance(self.expected, list) else [self.expected])
        elif self.operator == AssertionOperator.NOT_IN:
            passed = actual not in (self.expected if isinstance(self.expected, list) else [self.expected])
        elif self.operator == AssertionOperator.LESS_THAN:
            passed = actual < self.expected
        elif self.operator == AssertionOperator.GREATER_THAN:
            passed = actual > self.expected
        elif self.operator == AssertionOperator.LESS_THAN_OR_EQUALS:
            passed = actual <= self.expected
        elif self.operator == AssertionOperator.GREATER_THAN_OR_EQUALS:
            passed = actual >= self.expected
        else:
            passed = False
        
        message = f"Status code assertion '{self.name}'"
        if passed:
            message += " passed"
        else:
            message += f" failed: expected {self.operator.value} {self.expected}, got {actual}"
        
        return AssertionResult(
            name=self.name,
            passed=passed,
            expected=self.expected,
            actual=actual,
            message=message,
            assertion_type="status_code"
        )


class JSONPathAssertion(BaseAssertion):
    def __init__(self, name: str, path: str, operator: AssertionOperator, expected: Any = None):
        super().__init__(name, operator, expected)
        self.path = path

    def _get_value_by_path(self, data: Any, path: str) -> tuple[Any, bool]:
        current = data
        parts = path.replace('$.', '').replace('$.', '').split('.')
        
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None, False
            elif isinstance(current, list):
                try:
                    if part.isdigit():
                        index = int(part)
                        current = current[index]
                    else:
                        return None, False
                except (IndexError, ValueError):
                    return None, False
            else:
                return None, False
        
        return current, True

    def evaluate(self, response: Dict) -> AssertionResult:
        body = response.get('text', '')
        try:
            data = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            return AssertionResult(
                name=self.name,
                passed=False,
                expected=self.expected,
                actual=None,
                message=f"JSONPath assertion '{self.name}' failed: Response is not valid JSON",
                assertion_type="json_path"
            )
        
        actual, found = self._get_value_by_path(data, self.path)
        
        if self.operator == AssertionOperator.EXISTS:
            passed = found
        elif self.operator == AssertionOperator.NOT_EXISTS:
            passed = not found
        elif not found:
            passed = False
        elif self.operator == AssertionOperator.EQUALS:
            passed = actual == self.expected
        elif self.operator == AssertionOperator.NOT_EQUALS:
            passed = actual != self.expected
        elif self.operator == AssertionOperator.CONTAINS:
            passed = self.expected in str(actual)
        elif self.operator == AssertionOperator.MATCHES:
            passed = bool(re.search(str(self.expected), str(actual)))
        elif self.operator == AssertionOperator.IS_EMPTY:
            passed = actual is None or actual == '' or (isinstance(actual, (list, dict)) and len(actual) == 0)
        elif self.operator == AssertionOperator.IS_NOT_EMPTY:
            passed = actual is not None and actual != '' and (not isinstance(actual, (list, dict)) or len(actual) > 0)
        elif self.operator == AssertionOperator.IS_TYPE:
            passed = type(actual).__name__.lower() == str(self.expected).lower()
        else:
            passed = False
        
        message = f"JSONPath assertion '{self.name}'"
        if passed:
            message += " passed"
        else:
            message += f" failed: path '{self.path}' expected {self.operator.value} {self.expected}, got {actual}"
        
        return AssertionResult(
            name=self.name,
            passed=passed,
            expected=self.expected,
            actual=actual,
            message=message,
            assertion_type="json_path",
            details=f"Path: {self.path}"
        )


class HeaderAssertion(BaseAssertion):
    def __init__(self, name: str, header_name: str, operator: AssertionOperator, expected: Any = None):
        super().__init__(name, operator, expected)
        self.header_name = header_name

    def evaluate(self, response: Dict) -> AssertionResult:
        headers = response.get('headers', {})
        actual = headers.get(self.header_name, headers.get(self.header_name.lower(), headers.get(self.header_name.upper())))
        
        if self.operator == AssertionOperator.EXISTS:
            passed = actual is not None
        elif self.operator == AssertionOperator.NOT_EXISTS:
            passed = actual is None
        elif actual is None:
            passed = False
        elif self.operator == AssertionOperator.EQUALS:
            passed = str(actual).lower() == str(self.expected).lower()
        elif self.operator == AssertionOperator.CONTAINS:
            passed = str(self.expected).lower() in str(actual).lower()
        elif self.operator == AssertionOperator.MATCHES:
            passed = bool(re.search(str(self.expected), str(actual)))
        else:
            passed = False
        
        message = f"Header assertion '{self.name}'"
        if passed:
            message += " passed"
        else:
            message += f" failed: header '{self.header_name}' expected {self.operator.value} {self.expected}, got {actual}"
        
        return AssertionResult(
            name=self.name,
            passed=passed,
            expected=self.expected,
            actual=actual,
            message=message,
            assertion_type="header",
            details=f"Header: {self.header_name}"
        )


class ResponseTimeAssertion(BaseAssertion):
    def evaluate(self, response: Dict) -> AssertionResult:
        actual = response.get('response_time', 0)
        
        if self.operator == AssertionOperator.LESS_THAN:
            passed = actual < self.expected
        elif self.operator == AssertionOperator.LESS_THAN_OR_EQUALS:
            passed = actual <= self.expected
        elif self.operator == AssertionOperator.GREATER_THAN:
            passed = actual > self.expected
        elif self.operator == AssertionOperator.GREATER_THAN_OR_EQUALS:
            passed = actual >= self.expected
        elif self.operator == AssertionOperator.EQUALS:
            passed = actual == self.expected
        else:
            passed = False
        
        message = f"Response time assertion '{self.name}'"
        if passed:
            message += " passed"
        else:
            message += f" failed: expected {self.operator.value} {self.expected}ms, got {actual}ms"
        
        return AssertionResult(
            name=self.name,
            passed=passed,
            expected=self.expected,
            actual=actual,
            message=message,
            assertion_type="response_time",
            details=f"Threshold: {self.expected}ms"
        )


class BodyContainsAssertion(BaseAssertion):
    def evaluate(self, response: Dict) -> AssertionResult:
        body = response.get('text', '')
        
        if self.operator == AssertionOperator.CONTAINS:
            if isinstance(self.expected, str):
                passed = self.expected in body
            else:
                passed = str(self.expected) in body
        elif self.operator == AssertionOperator.NOT_CONTAINS:
            if isinstance(self.expected, str):
                passed = self.expected not in body
            else:
                passed = str(self.expected) not in body
        elif self.operator == AssertionOperator.MATCHES:
            passed = bool(re.search(str(self.expected), body))
        elif self.operator == AssertionOperator.IS_EMPTY:
            passed = body.strip() == ''
        elif self.operator == AssertionOperator.IS_NOT_EMPTY:
            passed = body.strip() != ''
        else:
            passed = False
        
        message = f"Body contains assertion '{self.name}'"
        if passed:
            message += " passed"
        else:
            message += f" failed: expected body to {self.operator.value} '{self.expected}'"
        
        return AssertionResult(
            name=self.name,
            passed=passed,
            expected=self.expected,
            actual=f"Body length: {len(body)} chars",
            message=message,
            assertion_type="body_contains"
        )


class AssertionEngine:
    def __init__(self, assertions: Optional[List[Dict]] = None):
        self.assertions: List[BaseAssertion] = []
        if assertions:
            for assertion_data in assertions:
                self.add(assertion_data)

    def add(self, assertion_data: Dict) -> bool:
        assertion_type = assertion_data.get('type')
        name = assertion_data.get('name', 'Unnamed assertion')
        
        try:
            operator = AssertionOperator(assertion_data.get('operator', 'equals'))
        except ValueError:
            return False
        
        if assertion_type == 'status_code':
            self.assertions.append(StatusCodeAssertion(
                name=name,
                operator=operator,
                expected=assertion_data.get('expected')
            ))
        elif assertion_type == 'json_path':
            self.assertions.append(JSONPathAssertion(
                name=name,
                path=assertion_data.get('path', ''),
                operator=operator,
                expected=assertion_data.get('expected')
            ))
        elif assertion_type == 'header':
            self.assertions.append(HeaderAssertion(
                name=name,
                header_name=assertion_data.get('header_name', ''),
                operator=operator,
                expected=assertion_data.get('expected')
            ))
        elif assertion_type == 'response_time':
            self.assertions.append(ResponseTimeAssertion(
                name=name,
                operator=operator,
                expected=assertion_data.get('expected')
            ))
        elif assertion_type == 'body_contains':
            self.assertions.append(BodyContainsAssertion(
                name=name,
                operator=operator,
                expected=assertion_data.get('expected')
            ))
        else:
            return False
        
        return True

    def clear(self):
        self.assertions.clear()

    def run(self, response: Dict) -> List[AssertionResult]:
        results = []
        for assertion in self.assertions:
            results.append(assertion.evaluate(response))
        return results

    @property
    def passed(self) -> bool:
        if not self.assertions:
            return True
        return all(isinstance(r, AssertionResult) and r.passed for r in self.run({}))

    @property
    def count(self) -> int:
        return len(self.assertions)

    def summary(self, results: List[AssertionResult]) -> Dict:
        return {
            'total': len(results),
            'passed': sum(1 for r in results if r.passed),
            'failed': sum(1 for r in results if not r.passed),
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'expected': r.expected,
                    'actual': r.actual,
                    'message': r.message,
                    'type': r.assertion_type
                }
                for r in results
            ]
        }
