"""Refoss extra broadcast - Refoss discovery across VLANs / subnets.

The core Refoss integration (library refoss-ha) discovers devices by sending
a UDP probe to 255.255.255.255:9988 every 30 s. Linux sends a limited
broadcast only out of the default-route interface, so devices on another
VLAN are never found, even if Home Assistant has an interface there.

This integration patches refoss_ha.discovery.Discovery.broadcast_msg so the
same probe is ALSO sent to subnet broadcasts of HA's network adapters and/or
manually configured addresses. Devices answer to HA:9989 and are then
discovered / IP-updated by the unchanged core integration.
"""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_ADDRESSES, CONF_AUTO, DOMAIN
from .helpers import (
    ACTIVE_ADDRESSES,
    async_adapter_broadcasts,
    async_patch_discovery,
    parse_addresses,
)

_LOGGER = logging.getLogger(__name__)

# Optional legacy YAML; imported into a UI config entry
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_ADDRESSES, default=[]): vol.All(
                    cv.ensure_list, [cv.string]
                ),
                vol.Optional(CONF_AUTO, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Import YAML configuration (if any) into a config entry."""
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    if not async_patch_discovery():
        return False

    opts = {**entry.data, **entry.options}
    addresses: list[str] = []
    if opts.get(CONF_AUTO, True):
        addresses += await async_adapter_broadcasts(hass)
    addresses += parse_addresses(opts.get(CONF_ADDRESSES, ""))
    addresses = list(dict.fromkeys(addresses))

    ACTIVE_ADDRESSES[:] = addresses
    _LOGGER.info(
        "Refoss discovery also probing: %s", ", ".join(addresses) or "(nothing)"
    )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload: stop sending extra probes (patch stays inert)."""
    ACTIVE_ADDRESSES.clear()
    return True
