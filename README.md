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

- The core **Refoss** integration set up in Home Assistant.
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
2. Install **Refoss extra broadcast (VLAN discovery)**.
3. Add the configuration below and restart Home Assistant.

### Manual
Copy `custom_components/refoss_extra_broadcast` into your Home Assistant
`config/custom_components/` folder, add the configuration and restart.

## Configuration

`configuration.yaml`:

```yaml
refoss_extra_broadcast:
  addresses:
    - 192.168.87.255   # broadcast of the VLAN/subnet with Refoss devices
    # - 192.168.87.65  # optional: device IPs as a unicast fallback
    # - 192.168.87.66
```

| Option      | Required | Description |
|-------------|----------|-------------|
| `addresses` | yes      | List of IPv4 addresses to send the discovery probe to (UDP 9988). Subnet broadcast addresses and/or device IPs. |

## Verify

After a restart, **Settings → System → Logs** should contain:

```
Refoss discovery also probing: 192.168.87.255
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

## Notes and limitations

- This is a **runtime monkey-patch** of `refoss_ha` (tested with
  `refoss-ha==1.2.5`). If a future library version renames
  `Discovery.broadcast_msg`, the patch stops applying and Home Assistant
  keeps working as before (without the extra probes). Please open an issue.
- The original `255.255.255.255` probe is still sent, so devices on the main
  network keep working.
- Patching is idempotent: reloading doesn't add duplicate probes.
- The cleaner long-term fix is a configurable discovery address in the core
  integration. This repo is a stop-gap and proof of concept for that.

## How it works (technical)

| | Core integration | With this add-on |
|---|---|---|
| Probe destination | `255.255.255.255:9988` | `255.255.255.255:9988` **plus** each configured address |
| Egress interface | default route only | the interface routing each configured address |
| Reply | device → HA `:9989` | unchanged |
| Discovery interval | 30 s (core) | unchanged |
