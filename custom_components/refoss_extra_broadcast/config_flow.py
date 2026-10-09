"""Config flow for Refoss extra broadcast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import CONF_ADDRESSES, CONF_AUTO, DOMAIN
from .helpers import async_adapter_broadcasts, parse_addresses


def _schema(auto: bool, addresses: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_AUTO, default=auto): bool,
            vol.Optional(CONF_ADDRESSES, default=addresses): str,
        }
    )


def _validate(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    errors: dict[str, str] = {}
    try:
        addrs = parse_addresses(user_input.get(CONF_ADDRESSES, ""))
    except ValueError:
        errors[CONF_ADDRESSES] = "invalid_address"
        addrs = []
    if not errors and not user_input.get(CONF_AUTO) and not addrs:
        errors["base"] = "nothing_to_probe"
    data = {CONF_AUTO: bool(user_input.get(CONF_AUTO)), CONF_ADDRESSES: ", ".join(addrs)}
    return data, errors


class RefossExtraBroadcastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First (and only) step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title="Refoss extra broadcast", data={}, options=data
                )

        detected = ", ".join(await async_adapter_broadcasts(self.hass))
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(True, ""),
            errors=errors,
            description_placeholders={"detected": detected or "-"},
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import from configuration.yaml."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        data, _ = _validate(
            {
                CONF_AUTO: import_data.get(CONF_AUTO, False),
                CONF_ADDRESSES: ", ".join(import_data.get(CONF_ADDRESSES, [])),
            }
        )
        return self.async_create_entry(
            title="Refoss extra broadcast", data={}, options=data
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options flow."""
        return RefossExtraBroadcastOptionsFlow()


class RefossExtraBroadcastOptionsFlow(OptionsFlow):
    """Change addresses after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(data=data)

        current = self.config_entry.options
        detected = ", ".join(await async_adapter_broadcasts(self.hass))
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(
                current.get(CONF_AUTO, True), current.get(CONF_ADDRESSES, "")
            ),
            errors=errors,
            description_placeholders={"detected": detected or "-"},
        )
