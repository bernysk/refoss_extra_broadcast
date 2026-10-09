"""Fixtures."""

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


ADAPTERS = [
    {
        "name": "enp0s18",
        "enabled": True,
        "auto": True,
        "default": True,
        "index": 2,
        "ipv4": [{"address": "192.168.88.10", "network_prefix": 24}],
        "ipv6": [],
    },
    {
        "name": "enp0s19",
        "enabled": True,
        "auto": False,
        "default": False,
        "index": 3,
        "ipv4": [{"address": "192.168.87.10", "network_prefix": 24}],
        "ipv6": [],
    },
    {
        "name": "disabled0",
        "enabled": False,
        "auto": False,
        "default": False,
        "index": 4,
        "ipv4": [{"address": "10.9.9.9", "network_prefix": 24}],
        "ipv6": [],
    },
]


@pytest.fixture(autouse=True)
def mock_adapters():
    """Mock HA network adapters."""
    with patch(
        "custom_components.refoss_extra_broadcast.helpers.network.async_get_adapters",
        return_value=ADAPTERS,
    ):
        yield
