import time
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import requests


class RunStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class RequestResult:
    request_name: str
    method: str
    url: str
    status: RunStatus = RunStatus.PENDING
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    assertions_passed: int = 0
    assertions_failed: int = 0
    assertion_results: List[Dict] = field(default_factory=list)
    error_message: Optional[str] = None
    response_body: Optional[str] = None
    response_headers: Optional[Dict] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'request_name': self.request_name,
            'method': self.method,
            'url': self.url,
            'status': self.status.value,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'assertions_passed': self.assertions_passed,
            'assertions_failed': self.assertions_failed,
            'assertion_results': self.assertion_results,
            'error_message': self.error_message,
            'timestamp': self.timestamp
        }


@dataclass
class CollectionRunResult:
    collection_name: str
    total_requests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total_time_ms: int = 0
    results: List[RequestResult] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'collection_name': self.collection_name,
            'total_requests': self.total_requests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'total_time_ms': self.total_time_ms,
            'results': [r.to_dict() for r in self.results],
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.passed / self.total_requests) * 100


class CollectionRunner:
    def __init__(self, stop_on_failure: bool = False, timeout: int = 30):
        self.stop_on_failure = stop_on_failure
        self.timeout = timeout
        self._current_result: Optional[CollectionRunResult] = None

    def run_single_request(self, request_data: Dict, assertions: Optional[List[Dict]] = None) -> RequestResult:
        result = RequestResult(
            request_name=request_data.get('name', 'Unnamed Request'),
            method=request_data.get('method', 'GET'),
            url=request_data.get('url', ''),
            timestamp=datetime.now().isoformat()
        )

        if not result.url:
            result.status = RunStatus.ERROR
            result.error_message = "No URL provided"
            return result

        try:
            start_time = time.time()
            
            response = requests.request(
                method=result.method,
                url=result.url,
                headers=request_data.get('headers', {}),
                params=request_data.get('params', {}),
                data=request_data.get('body'),
                timeout=self.timeout,
                verify=True
            )
            
            result.response_time_ms = int((time.time() - start_time) * 1000)
            result.status_code = response.status_code
            result.response_body = response.text
            result.response_headers = dict(response.headers)
            
            if assertions:
                from core.assertions import AssertionEngine
                engine = AssertionEngine(assertions)
                response_dict = {
                    'status_code': response.status_code,
                    'text': response.text,
                    'headers': dict(response.headers),
                    'response_time': result.response_time_ms
                }
                assertion_results = engine.run(response_dict)
                result.assertion_results = [
                    {
                        'name': r.name,
                        'passed': r.passed,
                        'expected': r.expected,
                        'actual': r.actual,
                        'message': r.message,
                        'type': r.assertion_type
                    }
                    for r in assertion_results
                ]
                result.assertions_passed = sum(1 for r in assertion_results if r.passed)
                result.assertions_failed = sum(1 for r in assertion_results if not r.passed)
                
                if result.assertions_failed > 0:
                    result.status = RunStatus.FAILED
                else:
                    result.status = RunStatus.PASSED
            else:
                if 200 <= result.status_code < 300:
                    result.status = RunStatus.PASSED
                else:
                    result.status = RunStatus.FAILED

        except requests.exceptions.Timeout:
            result.status = RunStatus.ERROR
            result.error_message = f"Request timed out after {self.timeout}s"
        except requests.exceptions.ConnectionError as e:
            result.status = RunStatus.ERROR
            result.error_message = f"Connection error: {str(e)}"
        except requests.exceptions.RequestException as e:
            result.status = RunStatus.ERROR
            result.error_message = f"Request failed: {str(e)}"
        except Exception as e:
            result.status = RunStatus.ERROR
            result.error_message = f"Unexpected error: {str(e)}"

        return result

    def run_collection(self, requests_list: List[Dict], collection_name: str = "Collection") -> CollectionRunResult:
        result = CollectionRunResult(
            collection_name=collection_name,
            total_requests=len(requests_list),
            started_at=datetime.now().isoformat()
        )

        start_time = time.time()

        for req in requests_list:
            if req.get('disabled', False):
                skip_result = RequestResult(
                    request_name=req.get('name', 'Unnamed Request'),
                    method=req.get('method', 'GET'),
                    url=req.get('url', ''),
                    status=RunStatus.SKIPPED,
                    timestamp=datetime.now().isoformat()
                )
                result.results.append(skip_result)
                result.skipped += 1
                continue

            req_result = self.run_single_request(
                req,
                assertions=req.get('assertions')
            )
            result.results.append(req_result)

            if req_result.status == RunStatus.PASSED:
                result.passed += 1
            elif req_result.status == RunStatus.FAILED:
                result.failed += 1
                if self.stop_on_failure:
                    logging.info(f"Stopping collection run due to failure: {req_result.request_name}")
                    break
            elif req_result.status == RunStatus.ERROR:
                result.errors += 1
                if self.stop_on_failure:
                    logging.info(f"Stopping collection run due to error: {req_result.request_name}")
                    break

        result.total_time_ms = int((time.time() - start_time) * 1000)
        result.completed_at = datetime.now().isoformat()

        return result

    def run_multiple(self, collections: List[Dict]) -> List[CollectionRunResult]:
        results = []
        for collection in collections:
            collection_result = self.run_collection(
                requests_list=collection.get('requests', []),
                collection_name=collection.get('name', 'Unnamed Collection')
            )
            results.append(collection_result)
        return results

    def generate_report(self, results: List[CollectionRunResult], format: str = 'json') -> str:
        if format == 'json':
            return self._generate_json_report(results)
        elif format == 'html':
            return self._generate_html_report(results)
        elif format == 'markdown':
            return self._generate_markdown_report(results)
        else:
            return self._generate_json_report(results)

    def _generate_json_report(self, results: List[CollectionRunResult]) -> str:
        return json.dumps([r.to_dict() for r in results], indent=2)

    def _generate_html_report(self, results: List[CollectionRunResult]) -> str:
        html = ['<!DOCTYPE html>', '<html>', '<head>',
                '<title>Collection Run Report</title>',
                '<style>',
                'body { font-family: Arial, sans-serif; margin: 20px; }',
                'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }',
                'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
                'th { background-color: #4CAF50; color: white; }',
                '.passed { color: green; }',
                '.failed { color: red; }',
                '.skipped { color: gray; }',
                '.error { color: orange; }',
                '</style>',
                '</head>', '<body>',
                '<h1>Collection Run Report</h1>']
        
        for result in results:
            html.append(f'<h2>{result.collection_name}</h2>')
            html.append(f'<p>Total: {result.total_requests} | '
                       f'<span class="passed">Passed: {result.passed}</span> | '
                       f'<span class="failed">Failed: {result.failed}</span> | '
                       f'<span class="skipped">Skipped: {result.skipped}</span> | '
                       f'<span class="error">Errors: {result.errors}</span></p>')
            html.append(f'<p>Success Rate: {result.success_rate:.1f}% | '
                       f'Total Time: {result.total_time_ms}ms</p>')
            
            html.append('<table><tr><th>Request</th><th>Method</th><th>URL</th>'
                       '<th>Status</th><th>Status Code</th><th>Time (ms)</th></tr>')
            
            for r in result.results:
                status_class = r.status.value
                html.append(f'<tr><td>{r.request_name}</td><td>{r.method}</td>'
                           f'<td>{r.url}</td><td class="{status_class}">{r.status.value}</td>'
                           f'<td>{r.status_code or "-"}</td>'
                           f'<td>{r.response_time_ms or "-"}</td></tr>')
            
            html.append('</table>')
        
        html.extend(['</body>', '</html>'])
        return '\n'.join(html)

    def _generate_markdown_report(self, results: List[CollectionRunResult]) -> str:
        md = ['# Collection Run Report\n']
        
        for result in results:
            md.append(f'\n## {result.collection_name}\n')
            md.append(f'- **Total Requests:** {result.total_requests}')
            md.append(f'- **Passed:** {result.passed}')
            md.append(f'- **Failed:** {result.failed}')
            md.append(f'- **Skipped:** {result.skipped}')
            md.append(f'- **Errors:** {result.errors}')
            md.append(f'- **Success Rate:** {result.success_rate:.1f}%')
            md.append(f'- **Total Time:** {result.total_time_ms}ms\n')
            
            md.append('| Request | Method | URL | Status | Code | Time (ms) |')
            md.append('|---------|--------|-----|--------|------|-----------|')
            
            for r in result.results:
                status = r.status.value.upper()
                md.append(f'| {r.request_name} | {r.method} | {r.url} | '
                          f'{status} | {r.status_code or "-"} | {r.response_time_ms or "-"} |')
        
        return '\n'.join(md)
