import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.base import (
    PluginBase,
    PluginMetadata,
    PluginHook,
    PluginType,
    RequestContext,
    ResponseContext,
    HookContext,
    PreRequestPlugin,
    PostRequestPlugin,
    TransformerPlugin,
    SecurityPlugin,
    ReporterPlugin,
    MockResponsePlugin,
    get_plugin_version,
    create_plugin_manifest,
)


class DummyPreRequestPlugin(PreRequestPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dummy_pre",
            version="1.0.0",
            author="Test",
            description="Dummy pre-request plugin",
            plugin_type=PluginType.CUSTOM,
            hooks=[PluginHook.PRE_REQUEST],
        )

    def pre_request(self, context: RequestContext) -> RequestContext:
        context.headers["X-Custom-Header"] = "added-by-plugin"
        return context


class DummyPostRequestPlugin(PostRequestPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dummy_post",
            version="1.0.0",
            author="Test",
            description="Dummy post-request plugin",
            plugin_type=PluginType.CUSTOM,
            hooks=[PluginHook.POST_REQUEST],
        )

    def post_request(
        self, request_context: RequestContext, response_context: ResponseContext
    ) -> ResponseContext:
        response_context.metadata["processed_by"] = "dummy_post"
        return response_context


class DummySecurityPlugin(SecurityPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dummy_security",
            version="1.0.0",
            author="Test",
            description="Dummy security plugin",
            plugin_type=PluginType.SECURITY,
            hooks=[PluginHook.PRE_REQUEST, PluginHook.POST_REQUEST],
        )

    def scan_request(self, context: RequestContext) -> list:
        findings = []
        if "password" in context.url.lower():
            findings.append({"type": "password_in_url", "severity": "high"})
        return findings

    def scan_response(self, context: ResponseContext) -> list:
        findings = []
        if context.status_code == 200:
            findings.append({"type": "success_response", "severity": "info"})
        return findings


class TestPluginMetadata:
    def test_plugin_metadata_creation(self):
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test description",
            plugin_type=PluginType.CUSTOM,
            hooks=[PluginHook.PRE_REQUEST],
        )
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.plugin_type == PluginType.CUSTOM
        assert PluginHook.PRE_REQUEST in metadata.hooks


class TestRequestContext:
    def test_request_context_creation(self):
        context = RequestContext(
            url="https://api.example.com/users",
            method="GET",
            headers={"Authorization": "Bearer token"},
        )
        assert context.url == "https://api.example.com/users"
        assert context.method == "GET"
        assert context.headers["Authorization"] == "Bearer token"
        assert context.timeout == 30.0


class TestResponseContext:
    def test_response_context_creation(self):
        context = ResponseContext(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"data": "test"},
            elapsed_ms=150.5,
        )
        assert context.status_code == 200
        assert context.body == {"data": "test"}
        assert context.elapsed_ms == 150.5
        assert context.error is None


class TestPreRequestPlugin:
    def test_plugin_instantiation(self):
        plugin = DummyPreRequestPlugin()
        assert plugin.metadata.name == "dummy_pre"
        assert plugin.enabled is True

    def test_plugin_config(self):
        plugin = DummyPreRequestPlugin({"custom_key": "custom_value"})
        assert plugin.config["custom_key"] == "custom_value"

    def test_pre_request_modifies_context(self):
        plugin = DummyPreRequestPlugin()
        context = RequestContext(url="https://api.example.com", method="GET")
        modified = plugin.pre_request(context)
        assert "X-Custom-Header" in modified.headers


class TestPostRequestPlugin:
    def test_plugin_instantiation(self):
        plugin = DummyPostRequestPlugin()
        assert plugin.metadata.name == "dummy_post"

    def test_post_request_modifies_response(self):
        plugin = DummyPostRequestPlugin()
        req_ctx = RequestContext(url="https://api.example.com", method="GET")
        resp_ctx = ResponseContext(status_code=200, body="{}")
        modified = plugin.post_request(req_ctx, resp_ctx)
        assert modified.metadata.get("processed_by") == "dummy_post"


class TestSecurityPlugin:
    def test_plugin_instantiation(self):
        plugin = DummySecurityPlugin()
        assert plugin.metadata.plugin_type == PluginType.SECURITY

    def test_scan_request_detects_password_in_url(self):
        plugin = DummySecurityPlugin()
        context = RequestContext(url="https://api.example.com?password=secret", method="GET")
        findings = plugin.scan_request(context)
        assert len(findings) == 1
        assert findings[0]["type"] == "password_in_url"

    def test_scan_response_adds_findings(self):
        plugin = DummySecurityPlugin()
        context = ResponseContext(status_code=200)
        findings = plugin.scan_response(context)
        assert len(findings) == 1
        assert findings[0]["type"] == "success_response"


class TestPluginHooks:
    def test_hook_context_creation(self):
        context = HookContext(
            plugin_name="test_plugin",
            hook_type=PluginHook.PRE_REQUEST,
            request_id="req-123",
        )
        assert context.plugin_name == "test_plugin"
        assert context.hook_type == PluginHook.PRE_REQUEST
        assert context.request_id == "req-123"


class TestGetPluginVersion:
    def test_get_plugin_version(self):
        version = get_plugin_version()
        assert isinstance(version, str)
        assert len(version) > 0


class TestCreatePluginManifest:
    def test_create_plugin_manifest(self):
        plugins = [DummyPreRequestPlugin(), DummyPostRequestPlugin()]
        manifest = create_plugin_manifest(plugins)
        assert "version" in manifest
        assert "plugins" in manifest
        assert len(manifest["plugins"]) == 2


class TestPluginEnableDisable:
    def test_plugin_enable_disable(self):
        plugin = DummyPreRequestPlugin()
        assert plugin.enabled is True
        plugin.enabled = False
        assert plugin.enabled is False
        plugin.enabled = True
        assert plugin.enabled is True


class TestPluginValidateConfig:
    def test_validate_config_no_schema(self):
        plugin = DummyPreRequestPlugin()
        errors = plugin.validate_config()
        assert errors == []

    def test_validate_config_missing_required(self):
        class PluginWithRequired(PreRequestPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="required_config",
                    version="1.0.0",
                    author="Test",
                    description="Test",
                    plugin_type=PluginType.CUSTOM,
                    hooks=[PluginHook.PRE_REQUEST],
                    config_schema={"required": ["api_key"]},
                )

            def pre_request(self, context: RequestContext) -> RequestContext:
                return context

        plugin = PluginWithRequired()
        errors = plugin.validate_config()
        assert "Missing required config key: api_key" in errors

    def test_validate_config_success(self):
        class PluginWithRequired(PreRequestPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    name="required_config",
                    version="1.0.0",
                    author="Test",
                    description="Test",
                    plugin_type=PluginType.CUSTOM,
                    hooks=[PluginHook.PRE_REQUEST],
                    config_schema={"required": ["api_key"]},
                )

            def pre_request(self, context: RequestContext) -> RequestContext:
                return context

        plugin = PluginWithRequired({"api_key": "secret"})
        errors = plugin.validate_config()
        assert errors == []
