import pytest
from engine.code_generator import (
    CodeGenerator, cURLGenerator, PythonRequestsGenerator,
    JavaScriptFetchGenerator, GoNetHttpGenerator
)


class TestCodeGenerator:
    def test_generate_curl(self):
        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users',
            'headers': {'Authorization': 'Bearer token'},
            'params': {'page': '1'}
        }
        code = CodeGenerator.generate(request, 'curl')
        assert 'curl' in code
        assert 'GET' in code
        assert 'api.example.com' in code

    def test_generate_python(self):
        request = {
            'method': 'POST',
            'url': 'https://api.example.com/users',
            'headers': {'Content-Type': 'application/json'},
            'body': '{"name": "John"}'
        }
        code = CodeGenerator.generate(request, 'python')
        assert 'requests' in code
        assert 'post' in code.lower()
        assert 'John' in code

    def test_generate_javascript(self):
        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users'
        }
        code = CodeGenerator.generate(request, 'javascript')
        assert 'fetch' in code
        assert 'example.com' in code

    def test_generate_go(self):
        request = {
            'method': 'GET',
            'url': 'https://api.example.com/users'
        }
        code = CodeGenerator.generate(request, 'go')
        assert 'net/http' in code
        assert 'http.NewRequest' in code

    def test_unsupported_language(self):
        request = {'method': 'GET', 'url': 'https://example.com'}
        with pytest.raises(ValueError):
            CodeGenerator.generate(request, 'unsupported_language')

    def test_available_languages(self):
        languages = CodeGenerator.available_languages()
        assert 'curl' in languages
        assert 'python' in languages
        assert 'javascript' in languages

    def test_display_name(self):
        assert CodeGenerator.display_name('curl') == 'cURL'
        assert CodeGenerator.display_name('python') == 'Python (requests)'
        assert CodeGenerator.display_name('javascript') == 'JavaScript (fetch)'


class TestCurlGenerator:
    def test_basic_get(self):
        generator = cURLGenerator()
        code = generator.generate({
            'method': 'GET',
            'url': 'https://api.example.com'
        })
        assert '-X GET' in code
        assert 'curl' in code

    def test_with_headers(self):
        generator = cURLGenerator()
        code = generator.generate({
            'method': 'POST',
            'url': 'https://api.example.com',
            'headers': {'Content-Type': 'application/json'}
        })
        assert '-H' in code
        assert 'Content-Type' in code

    def test_with_body(self):
        generator = cURLGenerator()
        code = generator.generate({
            'method': 'POST',
            'url': 'https://api.example.com',
            'body': '{"key": "value"}'
        })
        assert '-d' in code


class TestPythonGenerator:
    def test_basic_request(self):
        generator = PythonRequestsGenerator()
        code = generator.generate({
            'method': 'GET',
            'url': 'https://api.example.com'
        })
        assert 'requests.get' in code
        assert 'print(response' in code


class TestJavaScriptGenerator:
    def test_basic_fetch(self):
        generator = JavaScriptFetchGenerator()
        code = generator.generate({
            'method': 'GET',
            'url': 'https://api.example.com'
        })
        assert 'fetch(url' in code
        assert '.then' in code


class TestGoGenerator:
    def test_basic_request(self):
        generator = GoNetHttpGenerator()
        code = generator.generate({
            'method': 'GET',
            'url': 'https://api.example.com'
        })
        assert 'package main' in code
        assert 'http.NewRequest' in code
        assert 'client.Do' in code
