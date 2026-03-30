#!/usr/bin/env python3
"""
pyPost CLI Runner

Usage:
    pypost run collection.json [--env staging] [--stop-on-failure]
    pypost run --collection-id 123
    pypost mock-server [--port 5000]
    pypost export collection.json [--format openapi]
    pypost import openapi spec.json
    pypost security-scan https://api.example.com [--output report.json]
    pypost generate-data --template '{"name": "{{full_name}}", "email": "{{email}}"}' --count 5
    pypost audit-logs [--days 30] [--output audit.json]
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def run_collection(args) -> int:
    from engine.runner import CollectionRunner
    from database import DatabaseManager
    
    logging.info("Starting collection run...")
    
    runner = CollectionRunner(
        stop_on_failure=args.stop_on_failure,
        timeout=args.timeout if hasattr(args, 'timeout') else 30
    )
    
    requests_list = []
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    requests_list = data
                elif isinstance(data, dict):
                    if 'requests' in data:
                        requests_list = data['requests']
                    else:
                        requests_list = [data]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load collection file: {e}")
            return 1
    
    elif args.collection_id:
        db = DatabaseManager()
        collections = db.execute_query(
            "SELECT * FROM collections WHERE id = ?",
            (args.collection_id,)
        )
        if collections:
            collection = collections[0]
            request_data = collection.get('request_data')
            if request_data:
                if isinstance(request_data, str):
                    requests_list = [json.loads(request_data)]
                else:
                    requests_list = [request_data]
    
    if not requests_list:
        logging.error("No requests found to run")
        return 1
    
    collection_name = Path(args.file).stem if args.file else f"Collection {args.collection_id}"
    result = runner.run_collection(requests_list, collection_name)
    
    print(f"\n{'='*60}")
    print(f"Collection: {result.collection_name}")
    print(f"{'='*60}")
    print(f"Total Requests: {result.total_requests}")
    print(f"Passed: {result.passed}")
    print(f"Failed: {result.failed}")
    print(f"Skipped: {result.skipped}")
    print(f"Errors: {result.errors}")
    print(f"Success Rate: {result.success_rate:.1f}%")
    print(f"Total Time: {result.total_time_ms}ms")
    print(f"{'='*60}\n")
    
    if args.output:
        format_type = 'json'
        if args.output.endswith('.html'):
            format_type = 'html'
        elif args.output.endswith('.md'):
            format_type = 'markdown'
        
        report = runner.generate_report([result], format=format_type)
        with open(args.output, 'w') as f:
            f.write(report)
        logging.info(f"Report saved to {args.output}")
    
    return 0 if result.failed == 0 and result.errors == 0 else 1


def start_mock_server(args) -> int:
    from engine.mock_server import MockServer
    
    logging.info(f"Starting mock server on {args.host}:{args.port}...")
    
    server = MockServer(host=args.host, port=args.port)
    
    if args.config:
        try:
            with open(args.config, 'r') as f:
                endpoints = json.load(f)
                count = server.import_from_list(endpoints)
                logging.info(f"Loaded {count} endpoints from {args.config}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load mock config: {e}")
            return 1
    
    if args.example:
        for ep in MockServer.create_example_endpoints():
            server.add_endpoint(ep)
        logging.info("Added example endpoints")
    
    success = server.start()
    if success:
        print(f"Mock server running at {server.get_url()}")
        print("Press Ctrl+C to stop")
        try:
            import time
            while server.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
            print("\nMock server stopped")
    else:
        logging.error("Failed to start mock server")
        return 1
    
    return 0


def export_collection(args) -> int:
    from adapters.openapi_adapter import OpenAPIAdapter
    from database import DatabaseManager
    
    logging.info(f"Exporting collection to {args.file}...")
    
    db = DatabaseManager()
    
    collection_ids = []
    if args.collection_id:
        collection_ids = [args.collection_id]
    else:
        collections = db.execute_query("SELECT id FROM collections")
        collection_ids = [c['id'] for c in collections]
    
    collections_data = []
    for cid in collection_ids:
        coll = db.execute_query("SELECT * FROM collections WHERE id = ?", (cid,))
        if coll:
            collections_data.append(coll[0])
    
    if args.format == 'openapi':
        adapter = OpenAPIAdapter(db)
        spec = adapter.export_to_dict(
            collections_data,
            title=args.title or "pyPost Export",
            version=args.version or "1.0.0"
        )
        with open(args.file, 'w') as f:
            json.dump(spec, f, indent=2)
        logging.info(f"Exported to OpenAPI spec: {args.file}")
    
    elif args.format == 'postman':
        postman_format = _convert_to_postman_format(collections_data)
        with open(args.file, 'w') as f:
            json.dump(postman_format, f, indent=2)
        logging.info(f"Exported to Postman format: {args.file}")
    
    elif args.format == 'json':
        with open(args.file, 'w') as f:
            json.dump(collections_data, f, indent=2)
        logging.info(f"Exported to JSON: {args.file}")
    
    return 0


def _convert_to_postman_format(collections: List[Dict]) -> Dict:
    items = []
    
    for coll in collections:
        request_data = coll.get('request_data')
        if request_data:
            if isinstance(request_data, str):
                request_data = json.loads(request_data)
            
            items.append({
                "name": coll['name'],
                "request": {
                    "method": request_data.get('method', 'GET'),
                    "header": [
                        {"key": k, "value": v}
                        for k, v in request_data.get('headers', {}).items()
                    ],
                    "url": {
                        "raw": request_data.get('url', ''),
                        "query": [
                            {"key": k, "value": v}
                            for k, v in request_data.get('params', {}).items()
                        ]
                    },
                    "body": {
                        "mode": "raw",
                        "raw": request_data.get('body', '')
                    }
                }
            })
    
    return {
        "info": {
            "name": "pyPost Export",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": items
    }


def import_spec(args) -> int:
    from adapters.openapi_adapter import OpenAPIAdapter
    from database import DatabaseManager
    
    logging.info(f"Importing OpenAPI spec from {args.file}...")
    
    adapter = OpenAPIAdapter()
    
    try:
        collections = adapter.import_from_file(args.file)
    except FileNotFoundError:
        logging.error(f"File not found: {args.file}")
        return 1
    
    if not collections:
        logging.error("No collections found in spec")
        return 1
    
    db = DatabaseManager()
    imported = 0
    
    for collection in collections:
        name = collection.get('name', 'Imported')
        requests = collection.get('requests', [])
        
        for req in requests:
            try:
                db.execute_update(
                    "INSERT INTO collections (name, request_data) VALUES (?, ?)",
                    (f"{name}: {req.get('name', 'Request')}", json.dumps(req))
                )
                imported += 1
            except Exception as e:
                logging.warning(f"Failed to import request: {e}")
    
    logging.info(f"Imported {imported} requests from {len(collections)} collections")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='pyPost CLI - API Testing Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    run_parser = subparsers.add_parser('run', help='Run a collection')
    run_parser.add_argument('file', nargs='?', help='Collection file path')
    run_parser.add_argument('--collection-id', type=int, help='Collection ID from database')
    run_parser.add_argument('--env', '--environment', dest='environment', help='Environment name')
    run_parser.add_argument('--stop-on-failure', action='store_true', help='Stop on first failure')
    run_parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    run_parser.add_argument('-o', '--output', help='Output file for results')
    
    mock_parser = subparsers.add_parser('mock-server', help='Start mock server')
    mock_parser.add_argument('--host', default='127.0.0.1', help='Server host')
    mock_parser.add_argument('-p', '--port', type=int, default=5000, help='Server port')
    mock_parser.add_argument('-c', '--config', help='Mock endpoints config file')
    mock_parser.add_argument('--example', action='store_true', help='Add example endpoints')
    
    export_parser = subparsers.add_parser('export', help='Export collection')
    export_parser.add_argument('file', help='Output file path')
    export_parser.add_argument('--collection-id', type=int, help='Collection ID')
    export_parser.add_argument('--format', choices=['openapi', 'postman', 'json'], default='openapi')
    export_parser.add_argument('--title', help='API title for OpenAPI export')
    export_parser.add_argument('--version', help='API version for OpenAPI export')
    
    import_parser = subparsers.add_parser('import', help='Import OpenAPI spec')
    import_parser.add_argument('file', help='OpenAPI spec file path')
    
    security_parser = subparsers.add_parser('security-scan', help='Scan URL for security issues')
    security_parser.add_argument('url', help='URL to scan')
    security_parser.add_argument('--method', default='GET', help='HTTP method')
    security_parser.add_argument('--headers', help='JSON headers')
    security_parser.add_argument('--body', help='Request body')
    security_parser.add_argument('-o', '--output', help='Output file for report')
    
    data_parser = subparsers.add_parser('generate-data', help='Generate test data')
    data_parser.add_argument('--template', required=True, help='Template with placeholders')
    data_parser.add_argument('--count', type=int, default=1, help='Number of records to generate')
    data_parser.add_argument('--output', help='Output file')
    data_parser.add_argument('--format', choices=['json', 'csv', 'text'], default='text')
    
    audit_parser = subparsers.add_parser('audit-logs', help='View audit logs')
    audit_parser.add_argument('--days', type=int, default=30, help='Number of days to look back')
    audit_parser.add_argument('--output', help='Output file')
    audit_parser.add_argument('--format', choices=['json', 'csv'], default='json')
    audit_parser.add_argument('--event-type', help='Filter by event type')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if args.command == 'run':
        return run_collection(args)
    elif args.command == 'mock-server':
        return start_mock_server(args)
    elif args.command == 'export':
        return export_collection(args)
    elif args.command == 'import':
        return import_spec(args)
    elif args.command == 'security-scan':
        return security_scan(args)
    elif args.command == 'generate-data':
        return generate_data(args)
    elif args.command == 'audit-logs':
        return view_audit_logs(args)
    else:
        parser.print_help()
        return 0


def security_scan(args) -> int:
    from security.scanner import SecurityScanner, get_risk_level
    import core.audit as audit_module
    
    logging.info(f"Scanning: {args.url}")
    
    headers = {}
    body = None
    
    if args.headers:
        try:
            headers = json.loads(args.headers)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid headers JSON: {e}")
            return 1
    
    if args.body:
        try:
            body = json.loads(args.body)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid body JSON: {e}")
            return 1
    
    scanner = SecurityScanner()
    report = scanner.scan_request(args.url, args.method, headers, body)
    response_report = scanner.scan_response(args.url, args.method, 200, headers, body)
    
    all_findings = report.findings + response_report.findings
    risk_score = max(report.risk_score, response_report.risk_score)
    risk_level = get_risk_level(risk_score)
    
    print(f"\n{'='*60}")
    print(f"Security Scan Report")
    print(f"{'='*60}")
    print(f"URL: {args.url}")
    print(f"Method: {args.method}")
    print(f"Risk Score: {risk_score:.1f}/100 ({risk_level})")
    print(f"Total Findings: {len(all_findings)}")
    print(f"  Critical: {sum(1 for f in all_findings if f.severity.value == 'critical')}")
    print(f"  High: {sum(1 for f in all_findings if f.severity.value == 'high')}")
    print(f"  Medium: {sum(1 for f in all_findings if f.severity.value == 'medium')}")
    print(f"  Low: {sum(1 for f in all_findings if f.severity.value == 'low')}")
    print(f"{'='*60}\n")
    
    if all_findings:
        print("Findings:")
        for i, finding in enumerate(all_findings[:20], 1):
            print(f"  {i}. [{finding.severity.value.upper()}] {finding.title}")
            print(f"     {finding.description[:80]}...")
    
    try:
        audit_logger = audit_module.get_audit_logger()
        audit_logger.log_security_scan(
            url=args.url,
            findings_count=len(all_findings),
            risk_score=risk_score,
            critical_count=report.critical_count,
            high_count=report.high_count,
        )
    except Exception as e:
        logging.warning(f"Failed to log audit: {e}")
    
    if args.output:
        report_data = {
            "url": args.url,
            "method": args.method,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "findings": [f.to_dict() for f in all_findings],
        }
        with open(args.output, 'w') as f:
            json.dump(report_data, f, indent=2)
        logging.info(f"Report saved to {args.output}")
    
    return 0 if risk_score < 50 else 1


def generate_data(args) -> int:
    from utils.data_generator import DataGenerator, TemplateEngine
    
    logging.info("Generating test data...")
    
    generator = DataGenerator()
    engine = TemplateEngine(generator)
    
    results = []
    for _ in range(args.count):
        result = engine.generate_from_template(args.template)
        results.append(result)
    
    if args.format == 'json':
        output = json.dumps(results, indent=2)
    elif args.format == 'csv':
        output = '\n'.join(results)
    else:
        output = '\n---\n'.join(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logging.info(f"Generated {len(results)} records to {args.output}")
    else:
        print(output)
    
    return 0


def view_audit_logs(args) -> int:
    from core.audit import AuditLogger, AuditEventType
    from datetime import datetime, timedelta, timezone
    
    logging.info("Fetching audit logs...")
    
    logger = AuditLogger()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=args.days)
    
    event_types = None
    if args.event_type:
        try:
            event_types = [AuditEventType(args.event_type)]
        except ValueError:
            logging.error(f"Invalid event type: {args.event_type}")
            return 1
    
    entries = logger.get_entries(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        event_types=event_types,
        limit=1000,
    )
    
    print(f"\n{'='*60}")
    print(f"Audit Logs (Last {args.days} days)")
    print(f"{'='*60}")
    print(f"Total Events: {len(entries)}")
    
    if entries:
        event_counts = {}
        for entry in entries:
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1
        
        print("\nEvent Summary:")
        for event_type, count in sorted(event_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {event_type}: {count}")
    
    print(f"{'='*60}\n")
    
    if args.output:
        output = logger.export_logs(
            format=args.format,
            output_path=args.output,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        logging.info(f"Audit logs saved to {args.output}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
