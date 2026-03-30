import json
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class BaseCodeGenerator(ABC):
    @abstractmethod
    def generate(self, request_data: Dict) -> str:
        pass

    def _build_url(self, base_url: str, params: Optional[Dict] = None) -> str:
        if not params:
            return base_url
        
        param_parts = []
        for key, value in params.items():
            param_parts.append(f"{key}={value}")
        
        separator = '&' if '?' in base_url else '?'
        return f"{base_url}{separator}{'&'.join(param_parts)}"


class cURLGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        url = self._build_url(url, params)
        
        parts = [f'curl -X {method}']
        
        for key, value in headers.items():
            parts.append(f"-H '{key}: {value}'")
        
        if body and method in ['POST', 'PUT', 'PATCH']:
            if isinstance(body, dict):
                body = json.dumps(body)
            parts.append(f"-d '{body}'")
        
        parts.append(f"'{url}'")
        
        return ' \\\n  '.join(parts)


class PythonRequestsGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').lower()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        lines = ['import requests', '']
        
        lines.append(f"url = '{url}'")
        
        if headers:
            lines.append(f"\nheaders = {json.dumps(headers, indent=4)}")
        
        if params:
            lines.append(f"\nparams = {json.dumps(params, indent=4)}")
        
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            lines.append(f"\ndata = '{body}'")
        
        func_call = f"response = requests.{method}(url"
        if headers:
            func_call += ", headers=headers"
        if params:
            func_call += ", params=params"
        if body:
            func_call += ", data=data"
        func_call += ")"
        
        lines.append(f"\n{func_call}")
        lines.append("\nprint(response.status_code)")
        lines.append("print(response.json())")
        
        return '\n'.join(lines)


class JavaScriptFetchGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        url = self._build_url(url, params)
        
        lines = ["const url = '{}';".format(url)]
        
        if headers:
            lines.append("const headers = {")
            for i, (key, value) in enumerate(headers.items()):
                comma = ',' if i < len(headers) - 1 else ''
                lines.append(f"  '{key}': '{value}'{comma}")
            lines.append("};")
        
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            lines.append(f"const data = {json.dumps(body)};")
        
        lines.append("")
        
        options = ["const options = {"]
        options.append(f"  method: '{method}',")
        
        if headers:
            options.append("  headers: headers,")
        
        if body and method in ['POST', 'PUT', 'PATCH']:
            options.append("  body: JSON.stringify(data),")
            options.append("  headers: {")
            options.append("    'Content-Type': 'application/json',")
            if headers:
                for key, value in headers.items():
                    options.append(f"    '{key}': '{value}',")
            options.append("  },")
        
        options.append("};")
        lines.extend(options)
        
        lines.append("")
        lines.append("fetch(url, options)")
        lines.append("  .then(response => response.json())")
        lines.append("  .then(data => console.log(data))")
        lines.append("  .catch(error => console.error('Error:', error));")
        
        return '\n'.join(lines)


class JavaOkHttpGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        url = self._build_url(url, params)
        
        lines = [
            "import okhttp3.*;",
            "import java.io.IOException;",
            "",
            "public class ApiRequest {",
            "    public static void main(String[] args) throws IOException {",
            f"        OkHttpClient client = new OkHttpClient();",
            "",
            f"        HttpUrl.Builder urlBuilder = HttpUrl.parse(\"{url}\").newBuilder();",
            "",
        ]
        
        if headers:
            for key, value in headers.items():
                lines.append(f"        Request.Builder requestBuilder = new Request.Builder()")
                lines.append(f"            .addHeader(\"{key}\", \"{value}\")")
        
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            lines.append(f"        MediaType JSON = MediaType.parse(\"application/json; charset=utf-8\");")
            lines.append(f"        RequestBody body = RequestBody.create(JSON, \"{body}\");")
        
        method_lower = method.lower()
        lines.append("")
        lines.append(f"        Request request = new Request.Builder()")
        lines.append(f"            .url(\"{url}\")")
        lines.append(f"            .{method_lower}(", end="")
        if body:
            lines.append("body")
        else:
            lines.append("null")
        lines.append(")")
        
        if headers:
            for key, value in headers.items():
                lines.append(f"            .addHeader(\"{key}\", \"{value}\")")
        
        lines.append("            .build();")
        lines.append("")
        lines.append("        try (Response response = client.newCall(request).execute()) {")
        lines.append("            System.out.println(response.body().string());")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        
        return '\n'.join(lines)


class PHPHttpGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        url = self._build_url(url, params)
        
        lines = [
            "<?php",
            "",
            f"$url = '{url}';",
            "",
        ]
        
        if headers:
            lines.append("$headers = [")
            for key, value in headers.items():
                lines.append(f"    '{key}: {value}',")
            lines.append("];")
            lines.append("")
        
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            lines.append(f"$data = '{body}';")
            lines.append("")
        
        if method == 'GET':
            lines.append("$response = file_get_contents($url);")
        else:
            lines.append("$options = array(")
            lines.append("    'http' => array(")
            lines.append(f"        'method' => '{method}',")
            if body:
                lines.append("        'header' => 'Content-Type: application/json',")
                lines.append(f"        'content' => $data,")
            lines.append("    )")
            lines.append(");")
            lines.append("")
            lines.append("$context = stream_context_create($options);")
            lines.append("$response = file_get_contents($url, false, $context);")
        
        lines.append("")
        lines.append("var_dump($response);")
        lines.append("?>")
        
        return '\n'.join(lines)


class GoNetHttpGenerator(BaseCodeGenerator):
    def generate(self, request_data: Dict) -> str:
        method = request_data.get('method', 'GET').upper()
        url = request_data.get('url', '')
        headers = request_data.get('headers', {})
        params = request_data.get('params', {})
        body = request_data.get('body')
        
        url = self._build_url(url, params)
        
        lines = [
            "package main",
            "",
            "import (",
            '    "fmt"',
            '    "io/ioutil"',
            '    "net/http"',
        ]
        
        if body:
            lines.append('    "strings"')
        
        lines.append(")")
        lines.append("")
        lines.append("func main() {")
        lines.append(f'    url := "{url}"')
        lines.append("")
        
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            lines.append(f'    body := strings.NewReader(`{body}`)')
            lines.append("")
        
        lines.append("    req, err := http.NewRequest(")
        lines.append(f'        "{method}",')
        lines.append("        url,")
        
        if body:
            lines.append("        body,")
        else:
            lines.append("        nil,")
        
        lines.append("    )")
        lines.append("    if err != nil {")
        lines.append('        panic(err)')
        lines.append("    }")
        lines.append("")
        
        if headers:
            for key, value in headers.items():
                lines.append(f'    req.Header.Set("{key}", "{value}")')
        
        lines.append("")
        lines.append("    client := &http.Client{}")
        lines.append("    resp, err := client.Do(req)")
        lines.append("    if err != nil {")
        lines.append('        panic(err)')
        lines.append("    }")
        lines.append("    defer resp.Body.Close()")
        lines.append("")
        lines.append("    body, err := ioutil.ReadAll(resp.Body)")
        lines.append("    if err != nil {")
        lines.append('        panic(err)')
        lines.append("    }")
        lines.append('    fmt.Println(string(body))')
        lines.append("}")
        
        return '\n'.join(lines)


class CodeGenerator:
    LANGUAGES = {
        'curl': cURLGenerator,
        'python': PythonRequestsGenerator,
        'python-requests': PythonRequestsGenerator,
        'javascript': JavaScriptFetchGenerator,
        'js': JavaScriptFetchGenerator,
        'java': JavaOkHttpGenerator,
        'php': PHPHttpGenerator,
        'go': GoNetHttpGenerator,
    }

    LANG_DISPLAY_NAMES = {
        'curl': 'cURL',
        'python': 'Python (requests)',
        'javascript': 'JavaScript (fetch)',
        'java': 'Java (OkHttp)',
        'php': 'PHP',
        'go': 'Go (net/http)',
    }

    @classmethod
    def generate(cls, request_data: Dict, language: str) -> str:
        generator_class = cls.LANGUAGES.get(language.lower())
        if not generator_class:
            raise ValueError(f"Unsupported language: {language}")
        return generator_class().generate(request_data)

    @classmethod
    def available_languages(cls) -> List[str]:
        seen = set()
        result = []
        for lang in cls.LANGUAGES.keys():
            if lang not in seen and lang not in ['python-requests', 'js']:
                result.append(lang)
                seen.add(lang)
        return result

    @classmethod
    def display_name(cls, language: str) -> str:
        return cls.LANG_DISPLAY_NAMES.get(language, language.capitalize())

    @classmethod
    def all_display_names(cls) -> Dict[str, str]:
        return {
            lang: cls.display_name(lang)
            for lang in cls.available_languages()
        }
