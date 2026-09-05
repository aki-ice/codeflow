"""事件信封与 Topic 映射（Event Contract 的基础，所有服务共用）。"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

TOPIC_PREFIX = "codeflow"

TOPIC_RULES: list[tuple[str, str]] = [
    ("user.", f"{TOPIC_PREFIX}.user.events"),
    ("project.", f"{TOPIC_PREFIX}.project.events"),
    ("issue.", f"{TOPIC_PREFIX}.issue.events"),
    ("git.", f"{TOPIC_PREFIX}.git.events"),
    ("pipeline.", f"{TOPIC_PREFIX}.pipeline.events"),
    ("deployment.", f"{TOPIC_PREFIX}.deployment.events"),
    ("ai.", f"{TOPIC_PREFIX}.ai.events"),
    ("notification.", f"{TOPIC_PREFIX}.notification.events"),
]

DEFAULT_TOPIC = f"{TOPIC_PREFIX}.system.events"


def topic_for_event(event_type: str) -> str:
    for prefix, topic in TOPIC_RULES:
        if event_type.startswith(prefix):
            return topic
    return DEFAULT_TOPIC


def dlq_for(topic: str) -> str:
    return f"{topic}.DLQ"


@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def topic(self) -> str:
        return topic_for_event(self.event_type)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str | bytes) -> "Event":
        data = json.loads(raw)
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", ""),
        )
