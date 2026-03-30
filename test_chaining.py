import pytest
from core.extractors import (
    JSONPathExtractor, HeaderExtractor, RegexExtractor, 
    CookieExtractor, StatusCodeExtractor, ExtractorFactory
)
from core.chaining import ChainingEngine


class TestJSONPathExtractor:
    def test_simple_path(self):
        extractor = JSONPathExtractor("data.name")
        response = {'text': '{"data": {"name": "John"}}'}
        result = extractor.extract(response)
        assert result == "John"

    def test_array_index(self):
        extractor = JSONPathExtractor("users.0.name")
        response = {'text': '{"users": [{"name": "Alice"}]}'}
        result = extractor.extract(response)
        assert result == "Alice"

    def test_nested_path(self):
        extractor = JSONPathExtractor("a.b.c")
        response = {'text': '{"a": {"b": {"c": "value"}}}'.encode().decode()}
        result = extractor.extract(response)
        assert result == "value"


class TestHeaderExtractor:
    def test_extract_header(self):
        extractor = HeaderExtractor("Content-Type")
        response = {'headers': {'Content-Type': 'application/json'}}
        result = extractor.extract(response)
        assert result == 'application/json'

    def test_extract_case_insensitive(self):
        extractor = HeaderExtractor("X-Request-Id")
        response = {'headers': {'x-request-id': '123'}}
        result = extractor.extract(response)
        assert result == '123'


class TestRegexExtractor:
    def test_simple_match(self):
        extractor = RegexExtractor(r"id=(\d+)", group=1)
        response = {'text': 'user?id=12345&name=John'}
        result = extractor.extract(response)
        assert result == '12345'

    def test_no_match(self):
        extractor = RegexExtractor(r"notfound")
        response = {'text': 'hello world'}
        result = extractor.extract(response)
        assert result is None


class TestCookieExtractor:
    def test_extract_cookie(self):
        extractor = CookieExtractor("session_id")
        response = {'cookies': {'session_id': 'abc123'}}
        result = extractor.extract(response)
        assert result == 'abc123'


class TestExtractorFactory:
    def test_create_jsonpath(self):
        extractor = ExtractorFactory.create('jsonpath', {'path': 'data.id'})
        assert isinstance(extractor, JSONPathExtractor)

    def test_create_header(self):
        extractor = ExtractorFactory.create('header', {'header_name': 'Content-Type'})
        assert isinstance(extractor, HeaderExtractor)

    def test_create_regex(self):
        extractor = ExtractorFactory.create('regex', {'pattern': r'\d+'})
        assert isinstance(extractor, RegexExtractor)

    def test_create_invalid_type(self):
        extractor = ExtractorFactory.create('invalid', {})
        assert extractor is None


class TestChainingEngine:
    def test_set_and_get(self):
        engine = ChainingEngine()
        engine.set('token', 'abc123')
        assert engine.get('token') == 'abc123'

    def test_apply_to_text(self):
        engine = ChainingEngine()
        engine.set('user_id', '123')
        text = "https://api.example.com/users/{{user_id}}"
        result = engine.apply_to_text(text)
        assert result == "https://api.example.com/users/123"

    def test_apply_to_request(self):
        engine = ChainingEngine()
        engine.set('token', 'secret')
        request = {
            'url': 'https://api.example.com?token={{token}}',
            'headers': {'Authorization': 'Bearer {{token}}'}
        }
        result = engine.apply_to_request(request)
        assert result['url'] == 'https://api.example.com?token=secret'
        assert result['headers']['Authorization'] == 'Bearer secret'

    def test_has_pending_placeholders(self):
        engine = ChainingEngine()
        engine.set('defined', 'value')
        text = "url={{defined}}&other={{undefined}}"
        assert engine.has_pending_placeholders(text) is True

    def test_to_dict(self):
        engine = ChainingEngine()
        engine.set('key1', 'value1')
        engine.set('key2', 'value2')
        result = engine.to_dict()
        assert result == {'key1': 'value1', 'key2': 'value2'}

    def test_from_dict(self):
        data = {'key1': 'value1', 'key2': 'value2'}
        engine = ChainingEngine.from_dict(data)
        assert engine.get('key1') == 'value1'
        assert engine.get('key2') == 'value2'

    def test_extract_with_jsonpath(self):
        from core.extractors import JSONPathExtractor
        engine = ChainingEngine()
        response = {'text': '{"data": {"token": "xyz789"}}'}
        extractor = JSONPathExtractor("data.token")
        result = engine.extract(extractor, response, 'auth_token')
        assert result == 'xyz789'
        assert engine.get('auth_token') == 'xyz789'

    def test_clear(self):
        engine = ChainingEngine()
        engine.set('key', 'value')
        engine.clear()
        assert engine.get('key') is None
        assert len(engine.variables) == 0
