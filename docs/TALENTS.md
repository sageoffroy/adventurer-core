# Adventurer talents

Adventurer uses three native WotLK talent tabs:

- **Guardian** / **Guardián** — tanking, mitigation and survival.
- **Champion** / **Campeón** — physical and hybrid melee damage.
- **Scholar** / **Erudito** — magic damage and healing. Reserved in v0.

Each authored tree has its own JSON spec and its own Adventurer-owned Talent/Spell ID range. Guardian keeps the original `5000` / `290000` ranges; Champion uses `6000` / `300000`. Adding another tree must never reindex an existing tree.

## Guardian v0

Guardian is intentionally built from cloned Blizzard WotLK talent mechanics. Each clone receives an Adventurer-owned Talent ID and Spell ID unless the mechanic is script-sensitive and explicitly reuses its native spell rows. This keeps the original classes untouched while allowing Adventurer-specific cleanup of class, stance, form and spell-family restrictions.

The current Guardian tree contains **28 talents and 80 total ranks** across the normal 11 WotLK tiers. It combines generic mitigation and survival with avoidance, anti-control, resource efficiency, emergency tools, a shield progression, and a small set of active melee abilities.

## Champion v0

Champion also contains **28 talents and 80 total ranks** across 11 tiers. Its design deliberately mixes WotLK physical systems that normally belong to different classes: dual wielding, two-handed weapons, daggers and fist weapons, poisons, stealth, combo points, Rage, Energy and hybrid attack-power/spell-power interactions.

Where a native mechanic is safe and script-sensitive, Champion may reuse the Blizzard spell rows. Mechanics whose original spell-family, stance or resource restrictions would bind them to another class are cloned and sanitized. Champion also supports Adventurer-owned triggered child spells so proc talents can keep their event logic while applying custom generic buffs.

The first runtime pass is intentionally experimental for the most coupled mechanics. Heart Strike is converted to Rage and stripped of rune/runic-power behavior; Find Weakness is authored as generic damage; Turn the Tables buffs normal-attack critical chance; Blood Gorged and Cheat Death initially reuse their native rank spells so runtime testing can show whether their core-side behavior is class-bound.

The runtime test covers native talent infrastructure as well as the authored mechanics: all tabs must render, points must spend correctly, generated ranks must learn the intended spell IDs, prerequisite arrows must match the reference trees, and selections must survive logout/login. Source mechanics that prove class-, stance-, form-, rune-, resource-, or spell-family-dependent are replaced or sanitized after the first real-client smoke test.
