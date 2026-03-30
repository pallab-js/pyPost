import pytest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from plugins.manager import PluginManager, PluginInfo
from plugins.base import (
    PluginBase,
    PluginMetadata,
    PluginHook,
    PluginType,
    RequestContext,
    ResponseContext,
    PreRequestPlugin,
)


class TestPreRequestPluginImpl(PreRequestPlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="test_pre_plugin",
            version="1.0.0",
            author="Test",
            description="Test pre-request plugin",
            plugin_type=PluginType.CUSTOM,
            hooks=[PluginHook.PRE_REQUEST],
        )

    def pre_request(self, context: RequestContext) -> RequestContext:
        context.headers["X-Test-Header"] = "test_value"
        return context


class TestPluginManager:
    def test_manager_initialization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PluginManager(plugins_dir=tmpdir)
            assert manager._plugins_dir == tmpdir
            assert len(manager._plugins) == 0

    def test_register_builtin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        assert "test_plugin" in manager._built_in_plugins

    def test_load_builtin_plugin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        success = manager.load_plugin("test_plugin", {"enabled": True})
        assert success is True
        assert "test_plugin" in manager._plugins
        plugin = manager.get_plugin("test_plugin")
        assert plugin is not None

    def test_load_nonexistent_plugin(self):
        manager = PluginManager()
        success = manager.load_plugin("nonexistent_plugin")
        assert success is False

    def test_unload_plugin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        success = manager.unload_plugin("test_plugin")
        assert success is True
        assert "test_plugin" not in manager._plugins

    def test_unload_nonexistent_plugin(self):
        manager = PluginManager()
        success = manager.unload_plugin("nonexistent_plugin")
        assert success is False

    def test_enable_plugin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        success = manager.enable_plugin("test_plugin")
        assert success is True
        assert manager._plugins["test_plugin"].enabled is True

    def test_disable_plugin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        success = manager.disable_plugin("test_plugin")
        assert success is True
        assert manager._plugins["test_plugin"].enabled is False

    def test_list_plugins(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "test_plugin"
        assert plugins[0]["enabled"] is True

    def test_execute_pre_request(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        context = RequestContext(url="https://api.example.com", method="GET")
        modified = manager.execute_pre_request(context)
        assert "X-Test-Header" in modified.headers
        assert modified.headers["X-Test-Header"] == "test_value"

    def test_load_multiple_plugins(self):
        manager = PluginManager()
        manager.register_builtin("plugin1", TestPreRequestPluginImpl)
        manager.register_builtin("plugin2", TestPreRequestPluginImpl)
        manager.load_plugin("plugin1")
        manager.load_plugin("plugin2")
        assert len(manager._plugins) == 2

    def test_load_same_plugin_twice(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        success = manager.load_plugin("test_plugin")
        assert success is True

    def test_plugin_config(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        config = {"custom_config": "value"}
        manager.load_plugin("test_plugin", config)
        assert manager._config.get("test_plugin") == config

    def test_execute_pre_request_disabled_plugin(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        manager.disable_plugin("test_plugin")
        context = RequestContext(url="https://api.example.com", method="GET")
        modified = manager.execute_pre_request(context)
        assert "X-Test-Header" not in modified.headers

    def test_get_nonexistent_plugin(self):
        manager = PluginManager()
        plugin = manager.get_plugin("nonexistent")
        assert plugin is None

    def test_enable_nonexistent_plugin(self):
        manager = PluginManager()
        success = manager.enable_plugin("nonexistent")
        assert success is False

    def test_disable_nonexistent_plugin(self):
        manager = PluginManager()
        success = manager.disable_plugin("nonexistent")
        assert success is False

    def test_plugin_hooks_registration(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        hooks = manager._hooks[PluginHook.PRE_REQUEST]
        assert len(hooks) == 1
        assert hooks[0].metadata.name == "test_pre_plugin"

    def test_shutdown(self):
        manager = PluginManager()
        manager.register_builtin("test_plugin", TestPreRequestPluginImpl)
        manager.load_plugin("test_plugin")
        manager.shutdown()
        assert len(manager._plugins) == 0


class TestPluginInfo:
    def test_plugin_info_creation(self):
        info = PluginInfo(
            name="test",
            version="1.0.0",
            path="/path/to/plugin",
            module_name="plugin",
            plugin_class=TestPreRequestPluginImpl,
        )
        assert info.name == "test"
        assert info.version == "1.0.0"
        assert info.enabled is True
        assert info.instance is None
