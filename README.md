# skill-print

BeerCanLabs Agent Factory shared skill for printing documents, meeting agendas, and URLs to the home office printer.

## Architecture

In the BeerCanLabs Agent Factory model (DESIGN_AUTHORITY §6.1, §6.14):
- Agents run in network-isolated private subnets without raw internet or LAN access.
- Outbound requests are routed through the internal **Gatekeeper Egress** proxy (`routes: [print]`).
- The agent authenticates to the gatekeeper with its short-lived `FACTORY_RUN_TOKEN`.
- The Gatekeeper strips the run token, injects the vaulted `PRINT_API_TOKEN` held by Keymaster, and forwards the job to the home print bridge.

```
Agent Container (Donna / Higgins)
      │
      │  POST /jobs (Auth: Bearer $FACTORY_RUN_TOKEN)
      ▼
Gatekeeper Egress (Route: 'print')
      │  - Validates agent policy permit
      │  - Strips run token
      │  - Injects Keymaster-vaulted PRINT_API_TOKEN
      ▼
Hermes Print Bridge
      │
      ▼
CUPS / Office Printer (HP Color LaserJet Pro MFP 3301)
```

## Manifest (`skill.yaml`)

```yaml
id: print
version: 0.1.0
name: Print
description: Print documents, plain text, and URLs to the home office printer, query print queue, and check printer status.
language: python
entry: print_skill
requires:
  routes: [print]
```

## Python API Usage

```python
from print_skill import print_text, print_file, print_url, get_health, list_printers

# 1. Check printer readiness
health = get_health()
if health.get("ok"):
    # 2. Print briefing or agenda text
    res = print_text(
        "Morning Executive Agenda:\n- 9:00 AM: Engineering Standup\n- 11:30 AM: Architecture Review",
        title="Morning Agenda",
        copies=1,
    )
    print(f"Queued print job: {res.get('job_id')}")
```

## Tools Integration (Agent Cartridges)

When added to an agent's `cartridge.yaml`:
```yaml
skills:
  - id: print
    version: 0.1.0
```
The agent runtime exposes `tool_print_text`, `tool_print_url`, `tool_check_printer_health`, and `tool_list_printers`.

## Testing

```bash
python3 -m unittest discover
```
