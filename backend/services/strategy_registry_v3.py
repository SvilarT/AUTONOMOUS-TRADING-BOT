import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class StrategyDefinitionV3:
    """Immutable metadata for a research-plane strategy definition."""

    name: str
    version: str
    feature_schema_version: str
    implementation: str
    supported_actions: tuple[str, ...] = ("BUY", "SELL", "HOLD")
    research_only: bool = True
    description: str = ""

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["supported_actions"] = list(self.supported_actions)
        return payload

    def fingerprint(self) -> str:
        encoded = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class StrategyRegistryV3:
    """In-memory registry for reproducible research strategy definitions.

    This registry does not activate strategies, submit orders, or mutate runtime
    configuration. It exists to make historical replay evidence traceable to an
    immutable strategy identity.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, StrategyDefinitionV3] = {}
        self.register(
            StrategyDefinitionV3(
                name="multi_factor_baseline",
                version="v3.0.0",
                feature_schema_version="price_features_v3.0.0",
                implementation="services.strategy_service_v2.StrategyServiceV2",
                description="Transparent trend, momentum, extension, RSI, volatility, and drawdown baseline.",
            )
        )

    @staticmethod
    def key(name: str, version: str) -> str:
        return f"{name}:{version}"

    def register(self, definition: StrategyDefinitionV3) -> StrategyDefinitionV3:
        if not definition.research_only:
            raise ValueError("StrategyRegistryV3 accepts research-only definitions")
        if not definition.name.strip() or not definition.version.strip():
            raise ValueError("strategy name and version are required")
        if "HOLD" not in definition.supported_actions:
            raise ValueError("research strategies must support HOLD")

        key = self.key(definition.name, definition.version)
        existing = self._definitions.get(key)
        if existing and existing != definition:
            raise ValueError(f"strategy definition already exists with different metadata: {key}")
        self._definitions[key] = definition
        return definition

    def get(self, name: str, version: str) -> StrategyDefinitionV3:
        key = self.key(name, version)
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise KeyError(f"unknown research strategy definition: {key}") from exc

    def list_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                **definition.canonical_payload(),
                "fingerprint": definition.fingerprint(),
            }
            for definition in sorted(self._definitions.values(), key=lambda item: (item.name, item.version))
        ]
