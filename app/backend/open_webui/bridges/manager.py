import asyncio
import logging
from typing import Optional, Type

from open_webui.bridges.base import MessageBridge
from open_webui.bridges.types import PlatformInfo
from open_webui.models.bridges import (
    BridgeConnections,
    BridgeConnectionModel,
    BridgeThreads,
)

log = logging.getLogger(__name__)

# Global adapter registry
PLATFORM_ADAPTERS: dict[str, Type[MessageBridge]] = {}


def register_adapter(platform: str):
    """Decorator to register a platform adapter class."""

    def decorator(cls: Type[MessageBridge]):
        PLATFORM_ADAPTERS[platform] = cls
        log.info(f"Registered bridge adapter: {platform}")
        return cls

    return decorator


class BridgeManager:
    """Manages lifecycle of all bridge connections."""

    def __init__(self, app):
        self.app = app
        self._adapters: dict[str, MessageBridge] = {}  # connection_id -> adapter
        self._health_task: Optional[asyncio.Task] = None
        self._reconnect_delays: dict[str, float] = {}  # connection_id -> backoff seconds

    async def start(self) -> None:
        """Load enabled connections and start adapters."""
        log.info("BridgeManager starting...")

        # Import adapters to trigger @register_adapter decorators
        self._load_adapters()

        connections = BridgeConnections.get_enabled_connections()
        log.info(f"Found {len(connections)} enabled bridge connections")

        for conn in connections:
            await self._start_connection(conn)

        # Start periodic health check
        self._health_task = asyncio.create_task(self._health_check_loop())
        log.info("BridgeManager started")

    async def shutdown(self) -> None:
        """Disconnect all bridges and cancel health checks."""
        log.info("BridgeManager shutting down...")

        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        for connection_id in list(self._adapters.keys()):
            await self._stop_connection(connection_id)

        log.info("BridgeManager shut down")

    async def restart_connection(self, connection_id: str) -> bool:
        """Restart a specific bridge connection."""
        await self._stop_connection(connection_id)
        self._reconnect_delays.pop(connection_id, None)

        conn = BridgeConnections.get_connection_by_id(connection_id)
        if conn and conn.enabled:
            return await self._start_connection(conn)
        return False

    async def stop_connection(self, connection_id: str) -> None:
        """Stop a specific bridge connection."""
        await self._stop_connection(connection_id)

    def get_adapter(self, connection_id: str) -> Optional[MessageBridge]:
        """Get the adapter instance for a connection."""
        return self._adapters.get(connection_id)

    def get_all_statuses(self) -> dict[str, dict]:
        """Get status of all managed adapters."""
        statuses = {}
        for conn_id, adapter in self._adapters.items():
            statuses[conn_id] = {
                "connected": adapter.connected,
                "platform": type(adapter).__name__,
            }
        return statuses

    @staticmethod
    def get_available_platforms() -> list[dict]:
        """Get info about all registered platform adapters."""
        platforms = []
        for platform, adapter_cls in PLATFORM_ADAPTERS.items():
            info: PlatformInfo = adapter_cls.get_platform_info()
            platforms.append(
                {
                    "platform": info.platform,
                    "display_name": info.display_name,
                    "description": info.description,
                    "config_schema": [
                        {
                            "name": f.name,
                            "label": f.label,
                            "type": f.type,
                            "required": f.required,
                            "default": f.default,
                            "placeholder": f.placeholder,
                            "options": f.options,
                        }
                        for f in info.config_schema
                    ],
                    "supports_media": info.supports_media,
                    "supports_groups": info.supports_groups,
                }
            )
        return platforms

    def _load_adapters(self) -> None:
        """Import adapter modules to trigger registration."""
        try:
            import open_webui.bridges.adapters.whatsapp  # noqa: F401
        except ImportError as e:
            log.warning(f"Failed to load WhatsApp adapter: {e}")

    async def _start_connection(self, conn: BridgeConnectionModel) -> bool:
        """Instantiate and connect an adapter for a connection."""
        if conn.platform not in PLATFORM_ADAPTERS:
            log.error(f"No adapter registered for platform: {conn.platform}")
            BridgeConnections.update_connection_status(
                conn.id, "error", f"No adapter for platform: {conn.platform}"
            )
            return False

        adapter_cls = PLATFORM_ADAPTERS[conn.platform]
        adapter = adapter_cls(connection_id=conn.id, config=conn.config)

        BridgeConnections.update_connection_status(conn.id, "starting")

        try:
            success = await adapter.connect()
            if success:
                self._adapters[conn.id] = adapter
                self._reconnect_delays.pop(conn.id, None)
                BridgeConnections.update_connection_status(conn.id, "connected")
                log.info(f"Bridge connected: {conn.name} ({conn.platform})")
                return True
            else:
                BridgeConnections.update_connection_status(
                    conn.id, "error", "Connection failed"
                )
                return False
        except Exception as e:
            log.error(f"Failed to start bridge {conn.name}: {e}")
            BridgeConnections.update_connection_status(conn.id, "error", str(e))
            return False

    async def _stop_connection(self, connection_id: str) -> None:
        """Disconnect and remove an adapter."""
        adapter = self._adapters.pop(connection_id, None)
        if adapter:
            try:
                await adapter.disconnect()
            except Exception as e:
                log.error(f"Error disconnecting bridge {connection_id}: {e}")
            BridgeConnections.update_connection_status(connection_id, "disconnected")

    async def _health_check_loop(self) -> None:
        """Periodically check health of all connected bridges."""
        while True:
            try:
                await asyncio.sleep(60)
                for conn_id in list(self._adapters.keys()):
                    adapter = self._adapters.get(conn_id)
                    if not adapter:
                        continue

                    try:
                        healthy = await adapter.health_check()
                        if not healthy:
                            log.warning(f"Bridge unhealthy: {conn_id}")
                            await self._handle_unhealthy(conn_id)
                    except Exception as e:
                        log.error(f"Health check error for {conn_id}: {e}")
                        await self._handle_unhealthy(conn_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Health check loop error: {e}")

    async def _handle_unhealthy(self, connection_id: str) -> None:
        """Handle an unhealthy bridge with exponential backoff reconnection."""
        delay = self._reconnect_delays.get(connection_id, 30.0)
        self._reconnect_delays[connection_id] = min(delay * 2, 300.0)  # max 5 min

        log.info(f"Reconnecting bridge {connection_id} after {delay}s")
        await self._stop_connection(connection_id)

        await asyncio.sleep(delay)

        conn = BridgeConnections.get_connection_by_id(connection_id)
        if conn and conn.enabled:
            await self._start_connection(conn)
