<img src="custom_components/refoss_extra_broadcast/brand/icon.png" alt="icon" width="96" align="right">

# Refoss extra broadcast (VLAN discovery)

A small Home Assistant custom integration that lets the built-in
[Refoss integration](https://www.home-assistant.io/integrations/refoss/)
find Refoss devices (e.g. EM06 / EM16 energy monitors) that are on a
**different VLAN or subnet** than Home Assistant's default network interface.

It doesn't replace the core integration. It only adds extra discovery
probes. Entities, polling and history all stay with the core `refoss`
integration.

## The problem

The core integration (via the [`refoss-ha`](https://github.com/ashionky/refoss_ha)
library) discovers devices by sending a UDP probe to the **limited broadcast
address** `255.255.255.255:9988` every 30 seconds. Devices reply to Home
Assistant on UDP `9989`, and Home Assistant then polls them over HTTP.

Linux sends a limited broadcast only out of the **default-route interface**.
If your Refoss devices are in an IoT VLAN, Home Assistant never finds them.
This holds even if Home Assistant has a second network interface in that
VLAN. When a device's IP changes, the integration also can't update the IP,
and its entities show:

> This entity is no longer being provided by the refoss integration.

## What this integration does

It patches `refoss_ha.discovery.Discovery.broadcast_msg` at runtime so that
every discovery round **also** sends the same probe to the addresses you
configure, such as a subnet broadcast (`192.168.87.255`) or device IPs. The
OS routes these out of the matching interface. Devices reply as usual, and
the unchanged core integration discovers them or updates their IP.

## Requirements

- Home Assistant 2024.12 or newer, with the core **Refoss** integration set up.
- Home Assistant must be able to reach the devices' subnet:
  - **Recommended:** a second network interface in the IoT VLAN (static IP,
    **no gateway**), e.g. `192.168.87.10/24`. Subnet broadcast then works
    with no firewall changes.
  - **Or (unicast only):** the router allows HA → device UDP `9988`, and the
    replies back to HA on UDP `9989`. Stateful firewalls usually allow the
    replies automatically.

## Installation

### HACS (custom repository)
1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/bernysk/refoss_extra_broadcast`, category **Integration**.
2. Install **Refoss extra broadcast (VLAN discovery)** and restart Home Assistant.

### Manual
Copy `custom_components/refoss_extra_broadcast` into your Home Assistant
`config/custom_components/` folder and restart.

## Configuration (UI)

**Settings → Devices & services → Add integration → Refoss extra broadcast**

| Field | Default | Description |
|---|---|---|
| **Probe subnet broadcasts of all enabled network adapters** | on | Sends the probe to the subnet broadcast of every adapter enabled under *Settings → System → Network → Network adapter* (e.g. `192.168.88.255` and `192.168.87.255`). The dialog shows which broadcasts were detected. |
| **Extra addresses** | empty | Comma-separated IPv4 addresses: subnet broadcasts and/or device IPs (e.g. `192.168.87.255, 192.168.87.65`). Useful when HA has no interface in the device subnet and the router forwards unicast UDP 9988. |

You can change both later via **Configure** on the integration. Changes
apply immediately.

<details>
<summary>Legacy YAML (optional, imported once into the UI entry)</summary>

```yaml
refoss_extra_broadcast:
  auto_broadcast: false
  addresses:
    - 192.168.87.255
```
After the first start you can remove the YAML and manage everything in the UI.
</details>

## Verify

After setup, **Settings → System → Logs** should contain:

```
Refoss discovery also probing: 192.168.88.255, 192.168.87.255
```

Refoss entities should become available within about 30 seconds. For
troubleshooting:

```yaml
logger:
  default: warning
  logs:
    custom_components.refoss_extra_broadcast: debug
    refoss_ha: debug
```

## Icon

The integration ships its own icon in `custom_components/refoss_extra_broadcast/brand/`
(`icon.png` 256×256, `icon@2x.png` 512×512). Home Assistant 2026.3 and newer show it
automatically. Older versions show a generic placeholder. The source is `assets/icon.svg`.

## Development

```bash
pip install pytest-homeassistant-custom-component refoss-ha==1.2.5
pytest
```

## Notes and limitations

- This is a **runtime monkey-patch** of `refoss_ha` (tested with
  `refoss-ha==1.2.5`). If a future library version renames
  `Discovery.broadcast_msg`, the patch stops applying and Home Assistant
  keeps working as before (without the extra probes). Please open an issue.
- The original `255.255.255.255` probe is still sent, so devices on the main
  network keep working.
- Patching is idempotent: reloading doesn't add duplicate probes. Removing the
  integration stops the extra probes immediately.
- The cleaner long-term fix is a configurable discovery address in the core
  integration. This repo is a stop-gap and proof of concept for that.

## How it works (technical)

| | Core integration | With this add-on |
|---|---|---|
| Probe destination | `255.255.255.255:9988` | `255.255.255.255:9988` **plus** adapter subnet broadcasts and/or configured addresses |
| Egress interface | default route only | the interface routing each configured address |
| Reply | device → HA `:9989` | unchanged |
| Discovery interval | 30 s (core) | unchanged |
