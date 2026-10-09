"""Tests for setup, config flow, options and the discovery patch."""

from refoss_ha.discovery import Discovery

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.refoss_extra_broadcast.const import (
    CONF_ADDRESSES,
    CONF_AUTO,
    DOMAIN,
)
from custom_components.refoss_extra_broadcast.helpers import ACTIVE_ADDRESSES


class FakeTransport:
    def __init__(self):
        self.sent = []

    def sendto(self, data, addr):
        self.sent.append(addr)


async def _sent_by_discovery() -> list:
    d = Discovery()
    d.transport = FakeTransport()
    await d.broadcast_msg()
    return d.transport.sent


async def _create(hass: HomeAssistant, user_input: dict):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert "192.168.87.255" in result["description_placeholders"]["detected"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()
    return result


async def test_flow_auto_and_patch(hass: HomeAssistant) -> None:
    result = await _create(hass, {CONF_AUTO: True, CONF_ADDRESSES: "192.168.87.65"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert ACTIVE_ADDRESSES == ["192.168.88.255", "192.168.87.255", "192.168.87.65"]
    sent = await _sent_by_discovery()
    assert sent == [
        ("192.168.88.255", 9988),
        ("192.168.87.255", 9988),
        ("192.168.87.65", 9988),
        ("255.255.255.255", 9988),
    ]


async def test_flow_manual_only(hass: HomeAssistant) -> None:
    result = await _create(hass, {CONF_AUTO: False, CONF_ADDRESSES: "192.168.87.255"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert ACTIVE_ADDRESSES == ["192.168.87.255"]


async def test_flow_invalid_address(hass: HomeAssistant) -> None:
    result = await _create(hass, {CONF_AUTO: True, CONF_ADDRESSES: "192.168.87.999"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ADDRESSES: "invalid_address"}


async def test_flow_nothing_to_probe(hass: HomeAssistant) -> None:
    result = await _create(hass, {CONF_AUTO: False, CONF_ADDRESSES: ""})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "nothing_to_probe"}


async def test_options_update_and_unload(hass: HomeAssistant) -> None:
    await _create(hass, {CONF_AUTO: True, CONF_ADDRESSES: ""})
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_AUTO: False, CONF_ADDRESSES: "192.168.87.66, 192.168.87.65"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert ACTIVE_ADDRESSES == ["192.168.87.66", "192.168.87.65"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert ACTIVE_ADDRESSES == []
    assert await _sent_by_discovery() == [("255.255.255.255", 9988)]


async def test_yaml_import(hass: HomeAssistant) -> None:
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {CONF_ADDRESSES: ["192.168.87.255"]}}
    )
    await hass.async_block_till_done()
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].options == {CONF_AUTO: False, CONF_ADDRESSES: "192.168.87.255"}
    assert ACTIVE_ADDRESSES == ["192.168.87.255"]


async def test_patch_is_idempotent(hass: HomeAssistant) -> None:
    from custom_components.refoss_extra_broadcast.helpers import async_patch_discovery

    assert async_patch_discovery()
    first = Discovery.broadcast_msg
    assert async_patch_discovery()
    assert Discovery.broadcast_msg is first
