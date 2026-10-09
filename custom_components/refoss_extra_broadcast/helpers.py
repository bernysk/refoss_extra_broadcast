"""Helpers for Refoss extra broadcast."""

from __future__ import annotations

import ipaddress
import json
import logging
from typing import Any

from homeassistant.components import network
from homeassistant.core import HomeAssistant

from .const import DISCOVERY_PORT, PROBE_PAYLOAD

_LOGGER = logging.getLogger(__package__)

PROBE = json.dumps(PROBE_PAYLOAD).encode("utf-8")

# Addresses currently in use by the patched broadcast_msg. A module-level
# list so option changes only swap the content, never re-patch the class.
ACTIVE_ADDRESSES: list[str] = []
_PATCH_FLAG = "_refoss_extra_patched"


def parse_addresses(raw: str | list[str] | None) -> list[str]:
    """Parse a comma/space/newline separated list of IPv4 addresses.

    Raises ValueError on an invalid entry.
    """
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else raw.replace(",", " ").split()
    result: list[str] = []
    for item in items:
        item = str(item).strip()
        if not item:
            continue
        result.append(str(ipaddress.IPv4Address(item)))
    return list(dict.fromkeys(result))


async def async_adapter_broadcasts(hass: HomeAssistant) -> list[str]:
    """Return subnet broadcast addresses of all enabled HA network adapters."""
    result: list[str] = []
    for adapter in await network.async_get_adapters(hass):
        if not adapter["enabled"]:
            continue
        for ipv4 in adapter["ipv4"]:
            prefix = ipv4["network_prefix"]
            if prefix >= 31:
                continue
            net = ipaddress.IPv4Network(f"{ipv4['address']}/{prefix}", strict=False)
            if net.is_loopback or net.is_link_local:
                continue
            result.append(str(net.broadcast_address))
    return list(dict.fromkeys(result))


def async_patch_discovery() -> bool:
    """Patch refoss_ha Discovery.broadcast_msg once. Return True if patched."""
    try:
        from refoss_ha.discovery import Discovery  # noqa: PLC0415
    except ImportError:
        _LOGGER.error(
            "refoss-ha library not found - set up the core Refoss integration first"
        )
        return False

    original = Discovery.broadcast_msg
    if getattr(original, _PATCH_FLAG, False):
        return True

    async def broadcast_msg(self: Any, wait_for: int = 0):
        transport = getattr(self, "transport", None)
        if transport is not None:
            for addr in ACTIVE_ADDRESSES:
                try:
                    transport.sendto(PROBE, (addr, DISCOVERY_PORT))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Extra Refoss probe to %s failed: %s", addr, err)
        return await original(self, wait_for)

    setattr(broadcast_msg, _PATCH_FLAG, True)
    Discovery.broadcast_msg = broadcast_msg
    return True
