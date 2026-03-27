"""Notify platform for Signal Gateway integration."""

from __future__ import annotations

import logging

from homeassistant.components.notify import DOMAIN as NOTIFY_DOMAIN, NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.service import async_set_service_schema

from ..const import DOMAIN
from .entities import SignalContactNotifyEntity, SignalGroupNotifyEntity
from .service_schemas import GUI_SERVICE_SCHEMA, SERVICE_SCHEMA
from .service import SignalGatewayNotificationService

_LOGGER = logging.getLogger(__name__)


async def async_load_notify_service(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client,
    default_recipients: list[str],
    service_name: str,
) -> None:
    """Load and register the legacy notify service."""
    # Create the notification service for legacy support
    service = SignalGatewayNotificationService(hass, client, default_recipients)

    _LOGGER.debug(
        "Registering Signal Gateway notify service '%s' for entry %s",
        service_name,
        entry.entry_id,
    )
    hass.services.async_register(
        NOTIFY_DOMAIN,
        service_name,
        service.handle_service_call,
        schema=SERVICE_SCHEMA,
    )

    # Set service schema for GUI
    async_set_service_schema(
        hass,
        NOTIFY_DOMAIN,
        service_name,
        GUI_SERVICE_SCHEMA,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Signal Gateway notify entities from a config entry."""
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Signal Gateway client not found for entry %s", entry.entry_id)
        return False

    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data.client
    if not client:
        _LOGGER.error("Signal Gateway client not initialized")
        return False

    # Get default recipients and approved devices from config
    default_recipients = entry_data.default_recipients
    approved_devices = entry.data.get("approved_devices")
    coordinators = entry_data.coordinators
    service_name = entry_data.service_name

    # Load and register the legacy notify service
    await async_load_notify_service(
        hass, entry, client, default_recipients, service_name
    )

    # Create notify entities
    try:
        contacts = await client.list_contacts()
        groups = await client.list_groups()
    except Exception as err:  # pylint: disable=broad-exception-caught
        _LOGGER.error("Failed to fetch contacts and groups: %s", err)
        return True  # Still return True to register the legacy service

    entities: list[NotifyEntity] = []

    for contact in contacts:
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = coordinators.get(f"contact_{contact.uuid}")
            if coordinator:
                entities.append(SignalContactNotifyEntity(coordinator))

    for group in groups:
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = entry_data.get_group_coordinator(group)
            if coordinator:
                entities.append(SignalGroupNotifyEntity(coordinator))

    if async_add_entities:
        async_add_entities(entities, True)
        _LOGGER.info(
            "Created %d contact and %d group notify entities",
            len([e for e in entities if isinstance(e, SignalContactNotifyEntity)]),
            len([e for e in entities if isinstance(e, SignalGroupNotifyEntity)]),
        )

    return True


async def async_unload_notify_service(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Signal Gateway notify entry."""
    _LOGGER.info("Unloading Signal Gateway notify entry %s", entry.entry_id)
    data = hass.data[DOMAIN].get(entry.entry_id)
    service_name = data.service_name if data else None

    if service_name:
        _LOGGER.debug(
            "Unregistering Signal Gateway notify service '%s' for entry %s",
            service_name,
            entry.entry_id,
        )
        hass.services.async_remove(NOTIFY_DOMAIN, service_name)

    return True
