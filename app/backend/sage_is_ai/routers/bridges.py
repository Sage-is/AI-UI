import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sage_is_ai.models.bridges import (
    BridgeConnections,
    BridgeConnectionForm,
    BridgeConnectionModel,
    BridgeConnectionUpdateForm,
    BridgeThreads,
    BridgeThreadModel,
)
from sage_is_ai.utils.auth import get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()


############################
# List Bridge Connections
############################


@router.get("/", response_model=list[BridgeConnectionModel])
async def get_bridge_connections(user=Depends(get_admin_user)):
    return BridgeConnections.get_connections()


############################
# Create Bridge Connection
############################


@router.post("/create", response_model=Optional[BridgeConnectionModel])
async def create_bridge_connection(
    request: Request,
    form_data: BridgeConnectionForm,
    user=Depends(get_admin_user),
):
    connection = BridgeConnections.insert_new_connection(form_data, user.id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create bridge connection",
        )

    # Start the connection if enabled
    if connection.enabled:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if bridge_manager:
            await bridge_manager.restart_connection(connection.id)

    return connection


############################
# Available Platforms
# (must be before /{id} to avoid being shadowed)
############################


@router.get("/platforms/available")
async def get_available_platforms(user=Depends(get_admin_user)):
    from sage_is_ai.bridges.manager import BridgeManager

    return BridgeManager.get_available_platforms()


############################
# Get All Bridge Statuses
# (must be before /{id} to avoid being shadowed)
############################


@router.get("/status/all")
async def get_all_bridge_statuses(
    request: Request, user=Depends(get_admin_user)
):
    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if not bridge_manager:
        return {}
    return bridge_manager.get_all_statuses()


############################
# Webhook Receiver
# (must be before /{id} to avoid being shadowed)
############################


@router.post("/webhook/{connection_id}")
async def handle_bridge_webhook(request: Request, connection_id: str):
    """Receive webhook from external platform. No auth required — verified by adapter."""
    connection = BridgeConnections.get_connection_by_id(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )

    if not connection.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Connection is disabled",
        )

    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if not bridge_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge manager not available",
        )

    adapter = bridge_manager.get_adapter(connection_id)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Adapter not running",
        )

    body = await request.body()
    headers = dict(request.headers)

    # Verify webhook signature
    if not await adapter.verify_webhook_signature(body, headers):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse incoming message
    incoming = await adapter.handle_webhook(body, headers)
    if incoming is None:
        # Event was recognized but doesn't need processing (e.g. status update)
        return {"status": "ok"}

    # Process through pipeline
    from sage_is_ai.bridges.pipeline import MessagePipeline

    pipeline = MessagePipeline(request.app)
    await pipeline.process_incoming(incoming)

    return {"status": "ok"}


############################
# Get Bridge Connection
############################


@router.get("/{id}", response_model=Optional[BridgeConnectionModel])
async def get_bridge_connection(id: str, user=Depends(get_admin_user)):
    connection = BridgeConnections.get_connection_by_id(id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bridge connection not found",
        )
    return connection


############################
# Update Bridge Connection
############################


@router.post("/{id}/update", response_model=Optional[BridgeConnectionModel])
async def update_bridge_connection(
    request: Request,
    id: str,
    form_data: BridgeConnectionUpdateForm,
    user=Depends(get_admin_user),
):
    connection = BridgeConnections.update_connection_by_id(id, form_data)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bridge connection not found",
        )

    # Restart the connection to apply changes
    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if bridge_manager:
        if connection.enabled:
            await bridge_manager.restart_connection(connection.id)
        else:
            await bridge_manager.stop_connection(connection.id)

    return connection


############################
# Delete Bridge Connection
############################


@router.delete("/{id}/delete")
async def delete_bridge_connection(
    request: Request, id: str, user=Depends(get_admin_user)
):
    connection = BridgeConnections.get_connection_by_id(id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bridge connection not found",
        )

    # Stop the adapter
    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if bridge_manager:
        await bridge_manager.stop_connection(id)

    # Delete threads first
    BridgeThreads.delete_threads_by_connection_id(id)
    BridgeConnections.delete_connection_by_id(id)

    return {"status": True}


############################
# Restart Bridge Connection
############################


@router.post("/{id}/restart")
async def restart_bridge_connection(
    request: Request, id: str, user=Depends(get_admin_user)
):
    connection = BridgeConnections.get_connection_by_id(id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bridge connection not found",
        )

    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if not bridge_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge manager not available",
        )

    success = await bridge_manager.restart_connection(id)
    return {"status": success}


############################
# Toggle Bridge Connection
############################


@router.post("/{id}/toggle", response_model=Optional[BridgeConnectionModel])
async def toggle_bridge_connection(
    request: Request, id: str, user=Depends(get_admin_user)
):
    connection = BridgeConnections.toggle_connection_by_id(id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bridge connection not found",
        )

    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if bridge_manager:
        if connection.enabled:
            await bridge_manager.restart_connection(connection.id)
        else:
            await bridge_manager.stop_connection(connection.id)

    return connection


############################
# Health Check
############################


@router.get("/{id}/health")
async def get_bridge_health(
    request: Request, id: str, user=Depends(get_admin_user)
):
    bridge_manager = getattr(request.app.state, "bridge_manager", None)
    if not bridge_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bridge manager not available",
        )

    adapter = bridge_manager.get_adapter(id)
    if not adapter:
        return {"healthy": False, "message": "Adapter not running"}

    try:
        healthy = await adapter.health_check()
        return {"healthy": healthy}
    except Exception as e:
        return {"healthy": False, "message": str(e)}


############################
# List Threads (Debug)
############################


@router.get("/{id}/threads", response_model=list[BridgeThreadModel])
async def get_bridge_threads(id: str, user=Depends(get_admin_user)):
    return BridgeThreads.get_threads_by_connection_id(id)
