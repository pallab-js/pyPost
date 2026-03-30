import os
import sys
import json
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from threading import RLock

from .base import (
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
)


logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    name: str
    version: str
    path: str
    module_name: str
    plugin_class: Type[PluginBase]
    instance: Optional[PluginBase] = None
    enabled: bool = True
    errors: List[str] = field(default_factory=list)


class PluginManager:
    def __init__(self, plugins_dir: Optional[str] = None):
        self._plugins_dir = plugins_dir or self._get_default_plugins_dir()
        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[PluginHook, List[PluginBase]] = {h: [] for h in PluginHook}
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._built_in_plugins: Dict[str, Type[PluginBase]] = {}
        self._config: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def _get_default_plugins_dir(self) -> str:
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent
        return str(base / "plugins")

    def register_builtin(self, name: str, plugin_class: Type[PluginBase]) -> None:
        self._built_in_plugins[name] = plugin_class

    def discover_plugins(self) -> List[PluginInfo]:
        discovered = []
        if not os.path.exists(self._plugins_dir):
            logger.info(f"Plugins directory not found: {self._plugins_dir}")
            return discovered

        for entry in os.scandir(self._plugins_dir):
            if entry.is_file() and entry.name.endswith(".py") and entry.name != "__init__.py":
                try:
                    plugin_info = self._load_plugin_from_file(entry.path)
                    if plugin_info:
                        discovered.append(plugin_info)
                except Exception as e:
                    logger.error(f"Failed to load plugin from {entry.path}: {e}")

            elif entry.is_dir() and (entry.path / "__init__.py").exists():
                try:
                    plugin_info = self._load_plugin_from_directory(entry.path)
                    if plugin_info:
                        discovered.append(plugin_info)
                except Exception as e:
                    logger.error(f"Failed to load plugin from {entry.path}: {e}")

        return discovered

    def _load_plugin_from_file(self, path: str) -> Optional[PluginInfo]:
        module_name = Path(path).stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            return None

        metadata = getattr(plugin_class, "metadata", None)
        if not metadata:
            return None

        return PluginInfo(
            name=metadata.name,
            version=metadata.version,
            path=path,
            module_name=module_name,
            plugin_class=plugin_class,
        )

    def _load_plugin_from_directory(self, path: str) -> Optional[PluginInfo]:
        module_name = Path(path).name
        spec = importlib.util.spec_from_file_location(
            module_name, Path(path) / "__init__.py"
        )
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugin_class = self._find_plugin_class(module)
        if not plugin_class:
            return None

        metadata = getattr(plugin_class, "metadata", None)
        if not metadata:
            return None

        return PluginInfo(
            name=metadata.name,
            version=metadata.version,
            path=path,
            module_name=module_name,
            plugin_class=plugin_class,
        )

    def _find_plugin_class(self, module) -> Optional[Type[PluginBase]]:
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, PluginBase)
                and attr != PluginBase
            ):
                return attr
        return None

    def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        with self._lock:
            if name in self._plugins:
                logger.warning(f"Plugin '{name}' is already loaded")
                return True

            if name in self._built_in_plugins:
                plugin_class = self._built_in_plugins[name]
                instance = plugin_class(config)
                metadata = instance.metadata
                if metadata:
                    self._plugins[name] = PluginInfo(
                        name=name,
                        version=metadata.version,
                        path="builtin",
                        module_name=name,
                        plugin_class=plugin_class,
                        instance=instance,
                    )
                    self._register_hooks(instance)
                    self._config[name] = config or {}
                    return True
                return False

            discovered = self.discover_plugins()
            for plugin_info in discovered:
                if plugin_info.name == name:
                    try:
                        instance = plugin_info.plugin_class(config)
                        errors = instance.validate_config()
                        if errors:
                            plugin_info.errors = errors
                            logger.warning(
                                f"Plugin '{name}' has config errors: {errors}"
                            )
                        plugin_info.instance = instance
                        self._plugins[name] = plugin_info
                        self._register_hooks(instance)
                        self._config[name] = config or {}
                        instance.on_load()
                        return True
                    except Exception as e:
                        logger.error(f"Failed to instantiate plugin '{name}': {e}")
                        return False

            logger.error(f"Plugin '{name}' not found")
            return False

    def unload_plugin(self, name: str) -> bool:
        with self._lock:
            if name not in self._plugins:
                return False

            plugin_info = self._plugins[name]
            if plugin_info.instance:
                plugin_info.instance.on_unload()

            for hook_list in self._hooks.values():
                if plugin_info.instance in hook_list:
                    hook_list.remove(plugin_info.instance)

            del self._plugins[name]
            del self._config[name]
            return True

    def _register_hooks(self, plugin: PluginBase) -> None:
        for hook in plugin.metadata.hooks:
            if hook in self._hooks:
                self._hooks[hook].append(plugin)

    def enable_plugin(self, name: str) -> bool:
        with self._lock:
            if name not in self._plugins:
                return False
            self._plugins[name].enabled = True
            if self._plugins[name].instance:
                self._plugins[name].instance.enabled = True
            return True

    def disable_plugin(self, name: str) -> bool:
        with self._lock:
            if name not in self._plugins:
                return False
            self._plugins[name].enabled = False
            if self._plugins[name].instance:
                self._plugins[name].instance.enabled = False
            return True

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        plugin_info = self._plugins.get(name)
        return plugin_info.instance if plugin_info else None

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": info.name,
                "version": info.version,
                "enabled": info.enabled,
                "type": (
                    info.instance.metadata.plugin_type.value
                    if info.instance
                    else "unknown"
                ),
                "hooks": (
                    [h.value for h in info.instance.metadata.hooks]
                    if info.instance
                    else []
                ),
                "errors": info.errors,
            }
            for info in self._plugins.values()
        ]

    def execute_pre_request(
        self, context: RequestContext
    ) -> RequestContext:
        for plugin in self._hooks[PluginHook.PRE_REQUEST]:
            if plugin.enabled:
                try:
                    context = plugin.pre_request(context)
                except Exception as e:
                    logger.error(
                        f"Plugin '{plugin.metadata.name}' pre_request failed: {e}"
                    )
        return context

    def execute_post_request(
        self,
        request_context: RequestContext,
        response_context: ResponseContext,
    ) -> ResponseContext:
        for plugin in self._hooks[PluginHook.POST_REQUEST]:
            if plugin.enabled:
                try:
                    response_context = plugin.post_request(
                        request_context, response_context
                    )
                except Exception as e:
                    logger.error(
                        f"Plugin '{plugin.metadata.name}' post_request failed: {e}"
                    )
        return response_context

    def execute_mock_request(
        self, context: RequestContext
    ) -> Optional[ResponseContext]:
        for plugin in self._hooks.get(PluginHook.ON_MOCK_REQUEST, []):
            if plugin.enabled and isinstance(plugin, MockResponsePlugin):
                try:
                    if plugin.should_handle(context):
                        return plugin.get_response(context)
                except Exception as e:
                    logger.error(
                        f"Plugin '{plugin.metadata.name}' mock_request failed: {e}"
                    )
        return None

    def load_all(self) -> int:
        if self._loaded:
            return len(self._plugins)

        config_path = Path(self._plugins_dir) / "plugins.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load plugin config: {e}")

        for name in self._built_in_plugins:
            config = self._config.get(name, {})
            if config.get("enabled", True):
                self.load_plugin(name, config)

        self._loaded = True
        return len(self._plugins)

    def save_config(self) -> None:
        config_path = Path(self._plugins_dir) / "plugins.json"
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config = {
                name: {**cfg, "enabled": self._plugins[name].enabled}
                for name, cfg in self._config.items()
                if name in self._plugins
            }
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plugin config: {e}")

    def shutdown(self) -> None:
        self.save_config()
        self._executor.shutdown(wait=True)
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)
