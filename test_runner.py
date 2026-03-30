import pytest
from engine.runner import CollectionRunner, RunStatus, RequestResult, CollectionRunResult


class TestRequestResult:
    def test_to_dict(self):
        result = RequestResult(
            request_name='Test',
            method='GET',
            url='https://api.example.com',
            status=RunStatus.PASSED,
            status_code=200,
            response_time_ms=150
        )
        d = result.to_dict()
        assert d['request_name'] == 'Test'
        assert d['status'] == 'passed'
        assert d['status_code'] == 200


class TestCollectionRunResult:
    def test_success_rate_empty(self):
        result = CollectionRunResult(collection_name='Test', total_requests=0)
        assert result.success_rate == 0.0

    def test_success_rate_full(self):
        result = CollectionRunResult(collection_name='Test', total_requests=10, passed=8)
        assert result.success_rate == 80.0

    def test_to_dict(self):
        result = CollectionRunResult(
            collection_name='Test',
            total_requests=2,
            passed=1,
            failed=1
        )
        d = result.to_dict()
        assert d['collection_name'] == 'Test'
        assert d['total_requests'] == 2


class TestCollectionRunner:
    def test_run_single_request_no_url(self):
        runner = CollectionRunner()
        result = runner.run_single_request({})
        assert result.status == RunStatus.ERROR
        assert "No URL" in result.error_message

    def test_run_single_request_success(self, requests_mock):
        import requests
        requests_mock.get('https://httpbin.org/get', json={'status': 'ok'}, status_code=200)
        
        runner = CollectionRunner(timeout=10)
        result = runner.run_single_request({
            'name': 'Test Request',
            'method': 'GET',
            'url': 'https://httpbin.org/get'
        })
        
        assert result.request_name == 'Test Request'
        assert result.status_code == 200

    def test_run_collection(self, requests_mock):
        import requests
        requests_mock.get('https://httpbin.org/get', json={'id': 1})
        requests_mock.post('https://httpbin.org/post', json={'created': True})
        
        runner = CollectionRunner(timeout=10)
        requests_list = [
            {'name': 'Get', 'method': 'GET', 'url': 'https://httpbin.org/get'},
            {'name': 'Post', 'method': 'POST', 'url': 'https://httpbin.org/post'}
        ]
        
        result = runner.run_collection(requests_list, 'Test Collection')
        
        assert result.collection_name == 'Test Collection'
        assert result.total_requests == 2
        assert result.passed >= 0

    def test_stop_on_failure(self):
        runner = CollectionRunner(stop_on_failure=True)
        assert runner.stop_on_failure is True

    def test_generate_json_report(self, requests_mock):
        import requests
        requests_mock.get('https://example.com', text='ok')
        
        runner = CollectionRunner()
        result = runner.run_collection([{
            'name': 'Test',
            'method': 'GET',
            'url': 'https://example.com'
        }])
        
        report = runner.generate_report([result], format='json')
        assert 'Test' in report
        assert 'collection_name' in report

    def test_generate_markdown_report(self, requests_mock):
        import requests
        requests_mock.get('https://example.com', text='ok')
        
        runner = CollectionRunner()
        result = runner.run_collection([{
            'name': 'Test',
            'method': 'GET',
            'url': 'https://example.com'
        }])
        
        report = runner.generate_report([result], format='markdown')
        assert '# Collection Run Report' in report
        assert '| Request |' in report
