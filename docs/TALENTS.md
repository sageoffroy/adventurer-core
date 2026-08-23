# Adventurer talents

Adventurer uses three native WotLK talent tabs:

- **Guardian** / **Guardián** — tanking, mitigation and survival.
- **Champion** / **Campeón** — physical damage. Reserved in v0.
- **Scholar** / **Erudito** — magic damage and healing. Reserved in v0.

## Guardian v0

Guardian is intentionally built from cloned Blizzard WotLK talent mechanics. Each clone receives an Adventurer-owned Talent ID and Spell ID; it never points directly at the stock talent spell. This keeps the original classes untouched and lets Adventurer-specific cleanup happen independently.

The first playable pass contains 29 talents across the normal 11 WotLK tiers. It deliberately includes generic avoidance/armor/stamina, magic mitigation, emergency survival, a shield sub-path, and a small number of active tank tools.

The first runtime test is about native talent infrastructure rather than final balance: the talent panel must show Guardian/Champion/Scholar, Guardian points must spend correctly, cloned ranks must learn their custom spell IDs, and the selections must survive logout/login. Any source mechanic that proves class-, stance-, form-, rune-, or resource-dependent is replaced or sanitized after this smoke test.
