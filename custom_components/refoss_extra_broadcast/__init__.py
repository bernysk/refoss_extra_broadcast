"""Refoss extra broadcast.

The core Refoss integration (library refoss-ha) discovers devices by sending
a UDP probe to 255.255.255.255:9988 every 30 s. Linux sends a limited
broadcast only out of the default-route interface, so devices in another
VLAN are never found, even if Home Assistant has an interface in that VLAN.

This integration patches refoss_ha.discovery.Discovery.broadcast_msg so the
same probe is ALSO sent to extra addresses (subnet broadcasts such as
192.168.87.255, or device IPs). Devices answer to HA:9989 and are then
discovered / IP-updated by the unchanged core integration.

configuration.yaml:
    refoss_extra_broadcast:
      addresses:
        - 192.168.87.255
"""

from __future__ import annotations

import json
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "refoss_extra_broadcast"
CONF_ADDRESSES = "addresses"
DISCOVERY_PORT = 9988
# Same probe payload the refoss-ha library sends
PROBE = json.dumps(
    {"id": "48cbd88f969eb3c486085cfe7b5eb1e4", "devName": "*"}
).encode("utf-8")

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Required(CONF_ADDRESSES): vol.All(cv.ensure_list, [cv.string])}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Patch refoss-ha discovery to probe extra addresses."""
    addresses: list[str] = config[DOMAIN][CONF_ADDRESSES]

    try:
        from refoss_ha.discovery import Discovery  # noqa: PLC0415
    except ImportError:
        _LOGGER.error("refoss-ha not installed - set up the Refoss integration first")
        return False

    original = Discovery.broadcast_msg
    if getattr(original, "_refoss_extra_patched", False):
        return True

    async def broadcast_msg(self, wait_for: int = 0):
        transport = getattr(self, "transport", None)
        if transport is not None:
            for addr in addresses:
                try:
                    transport.sendto(PROBE, (addr, DISCOVERY_PORT))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Extra refoss probe to %s failed: %s", addr, err)
        return await original(self, wait_for)

    broadcast_msg._refoss_extra_patched = True  # type: ignore[attr-defined]
    Discovery.broadcast_msg = broadcast_msg
    _LOGGER.info("Refoss discovery also probing: %s", ", ".join(addresses))
    return True
