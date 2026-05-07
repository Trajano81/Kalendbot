---
name: reference_data_structure
description: KalendBot data structure - proveedores are orgs, contactos are persons, from Excel columns
type: reference
---

- **Proveedores** (`kalendbot-data/proveedores/`): Organizations/companies from Excel "Mapa de partners" column
- **Contactos** (`kalendbot-data/contactos/`): Individual persons from Excel column L (name) + column M (phone)
- **Flyer responsibility** (column N): If a name appears → that person is responsible. If blank → Hanna van Rijsse (Content Manager)
- A provider can have multiple contacts; a contact belongs to one provider
- Calendar: `kalendbot-data/calendario-2026.json` — 31 events
- Config: `kalendbot-data/config/` — tiers, precedencia, restricciones, eventos-externos
