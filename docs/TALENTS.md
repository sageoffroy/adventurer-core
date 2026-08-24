# Adventurer talents

Adventurer uses three native WotLK talent tabs:

- **Guardian** / **Guardián** — tanking, mitigation and survival.
- **Champion** / **Campeón** — physical damage. Reserved in v0.
- **Scholar** / **Erudito** — magic damage and healing. Reserved in v0.

## Guardian v0

Guardian is intentionally built from cloned Blizzard WotLK talent mechanics. Each clone receives an Adventurer-owned Talent ID and Spell ID unless the mechanic is script-sensitive and explicitly reuses its native spell rows. This keeps the original classes untouched while allowing Adventurer-specific cleanup of class, stance, form and spell-family restrictions.

The current Guardian tree contains **28 talents and 80 total ranks** across the normal 11 WotLK tiers. It combines generic mitigation and survival with avoidance, anti-control, resource efficiency, emergency tools, a shield progression, and a small set of active melee abilities.

The runtime test is about native talent infrastructure as well as the authored mechanics: the talent panel must show Guardian/Champion/Scholar, Guardian points must spend correctly, generated ranks must learn the intended spell IDs, prerequisite arrows must match the reference tree, and the selections must survive logout/login. Source mechanics that are class-, stance-, form-, rune-, resource-, or spell-family-dependent are reused only when safe; otherwise they are cloned and sanitized for Adventurer.
