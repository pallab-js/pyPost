from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import importlib.metadata


class PluginHook(Enum):
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    PRE_COLLECTION_RUN = "pre_collection_run"
    POST_COLLECTION_RUN = "post_collection_run"
    ON_ASSERTION_FAILURE = "on_assertion_failure"
    ON_ERROR = "on_error"
    ON_MOCK_REQUEST = "on_mock_request"


class PluginType(Enum):
    SECURITY = "security"
    AUTHENTICATION = "authentication"
    TRANSFORMER = "transformer"
    REPORTER = "reporter"
    VALIDATOR = "validator"
    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    hooks: List[PluginHook] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None


@dataclass
class HookContext:
    plugin_name: str
    hook_type: PluginHook
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: Optional[str] = None
    collection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestContext:
    url: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Any] = None
    params: Dict[str, str] = field(default_factory=dict)
    auth: Optional[Dict[str, Any]] = None
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseContext:
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    elapsed_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or {}
        self._enabled = True
        self._metadata: Optional[PluginMetadata] = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        pass

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @config.setter
    def config(self, value: Dict[str, Any]) -> None:
        self._config = value
        self._on_config_changed()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def _on_config_changed(self) -> None:
        pass

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def validate_config(self) -> List[str]:
        errors = []
        schema = self.metadata.config_schema
        if not schema:
            return errors
        required = schema.get("required", [])
        for key in required:
            if key not in self._config:
                errors.append(f"Missing required config key: {key}")
        return errors


class PreRequestPlugin(PluginBase):
    @abstractmethod
    def pre_request(self, context: RequestContext) -> RequestContext:
        pass


class PostRequestPlugin(PluginBase):
    @abstractmethod
    def post_request(
        self, 
        request_context: RequestContext, 
        response_context: ResponseContext
    ) -> ResponseContext:
        pass


class TransformerPlugin(PluginBase):
    @abstractmethod
    def transform_request(self, context: RequestContext) -> RequestContext:
        pass

    @abstractmethod
    def transform_response(self, context: ResponseContext) -> ResponseContext:
        pass


class SecurityPlugin(PluginBase):
    @abstractmethod
    def scan_request(self, context: RequestContext) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def scan_response(self, context: ResponseContext) -> List[Dict[str, Any]]:
        pass


class ReporterPlugin(PluginBase):
    @abstractmethod
    def generate_report(
        self, 
        collection_results: List[Dict[str, Any]], 
        format: str = "json"
    ) -> Any:
        pass

    @abstractmethod
    def export_report(self, report: Any, path: str) -> bool:
        pass


class MockResponsePlugin(PluginBase):
    @abstractmethod
    def should_handle(self, request_context: RequestContext) -> bool:
        pass

    @abstractmethod
    def get_response(self, request_context: RequestContext) -> ResponseContext:
        pass


def get_plugin_version() -> str:
    try:
        return importlib.metadata.version("pyPost")
    except importlib.metadata.PackageNotFoundError:
        return "0.1.0"


def create_plugin_manifest(plugins: List[PluginBase]) -> Dict[str, Any]:
    return {
        "version": get_plugin_version(),
        "plugins": [
            {
                "name": p.metadata.name,
                "version": p.metadata.version,
                "type": p.metadata.plugin_type.value,
                "hooks": [h.value for h in p.metadata.hooks],
                "author": p.metadata.author,
                "description": p.metadata.description,
            }
            for p in plugins
        ],
    }
