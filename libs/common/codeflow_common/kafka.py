"""Kafka 生产者/发布器（各服务共用）。Kafka 未启用时降级为日志。"""

import logging
from typing import TYPE_CHECKING, Protocol

from codeflow_common.envelope import Event

if TYPE_CHECKING:
    from aiokafka import AIOKafkaProducer

logger = logging.getLogger("codeflow.events")


class EventPublisher(Protocol):
    async def publish(self, event: Event) -> None: ...


class LogEventPublisher:
    async def start(self) -> None:
        return None

    async def publish(self, event: Event) -> None:
        logger.info(
            "event published type=%s id=%s topic=%s payload=%s",
            event.event_type,
            event.event_id,
            event.topic(),
            event.payload,
        )

    async def stop(self) -> None:
        return None


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str, client_id: str = "codeflow-producer") -> None:
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            acks="all",
            enable_idempotence=True,
        )
        await producer.start()
        self._producer = producer
        logger.info("kafka producer started: %s", self.bootstrap_servers)

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, event: Event) -> None:
        producer = self._producer
        if producer is None:
            raise RuntimeError("kafka producer not started")
        await producer.send_and_wait(
            event.topic(),
            value=event.to_json().encode("utf-8"),
            key=event.event_id.encode("utf-8"),
        )
