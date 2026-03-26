"""Dynamic plugin loader for strategies and exchange connectors.

This module provides functions to discover and instantiate strategy and
connector classes based on a configuration file.  It uses Python’s
``importlib`` to load modules at runtime.  Plugins must reside in the
``plugins`` package and register classes that inherit from the
``AbstractStrategy`` or ``AbstractExchangeConnector`` base classes defined in
``core.strategy_engine`` and ``core.execution_router``, respectively.

Example ``config.yml`` snippet:

```yaml
strategies:
  - module: plugins.sample_strategy
    class: SimpleMovingAverageStrategy
connectors:
  - module: plugins.sample_connector
    class: MockConnector
```
"""

from __future__ import annotations

import importlib
import inspect
from typing import Dict, List, Any

from .core.strategy_engine import AbstractStrategy
from .core.execution_router import AbstractExchangeConnector


def load_class(module_name: str, class_name: str):
    """Dynamically load a class from a module."""
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise ImportError(f"Class {class_name} not found in module {module_name}")
    return cls


def load_strategies(config: Dict[str, Any]) -> List[AbstractStrategy]:
    strategies: List[AbstractStrategy] = []
    for entry in config.get("strategies", []):
        module_name = entry.get("module")
        class_name = entry.get("class")
        cls = load_class(module_name, class_name)
        if not inspect.isclass(cls) or not issubclass(cls, AbstractStrategy):
            raise TypeError(f"{class_name} in {module_name} is not a subclass of AbstractStrategy")
        strategies.append(cls())
    return strategies


def load_connectors(config: Dict[str, Any]) -> List[AbstractExchangeConnector]:
    connectors: List[AbstractExchangeConnector] = []
    for entry in config.get("connectors", []):
        module_name = entry.get("module")
        class_name = entry.get("class")
        cls = load_class(module_name, class_name)
        if not inspect.isclass(cls) or not issubclass(cls, AbstractExchangeConnector):
            raise TypeError(f"{class_name} in {module_name} is not a subclass of AbstractExchangeConnector")
        params = entry.get("params", {})
        connectors.append(cls(**params))
    return connectors
