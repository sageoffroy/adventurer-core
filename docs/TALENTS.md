# Adventurer talents

Adventurer currently authors native WotLK talent tabs through generated Talent/Spell DBC rows:

- **Guardian** / **Guardián** — tanking, mitigation and survival.
- **Champion** / **Campeón** — physical and hybrid melee damage. Conceptually this tree is evolving toward **Mercenary / Mercenario**.
- **Scholar** / **Erudito** — magic damage and healing. Reserved in the current client pass.

Each authored tree has its own JSON spec and its own Adventurer-owned Talent/Spell ID range. Guardian keeps the original `5000` / `290000` ranges; Champion uses `6000` / `300000`. Adding another tree must never reindex an externally stable Adventurer spell ID.

## Build-depth rule

Talent trees are designed around viable builds rather than around filling an arbitrary rank total.

- level 60: 51 points; 31/20, 30/21 and comparable hybrids must work;
- level 70: 61 points;
- level 80: 71 points;
- roughly 10 points is a dip, 20 points is a functional secondary package, and 30 points should already provide a complete tree identity;
- 40+ points are advanced specialization and the deepest rows are optional luxury/capstone territory.

A tree therefore does **not** need 80 available ranks. Weak 5/5 filler and mandatory corridors are deliberately avoided. Prerequisites are used only when the mechanical relationship is obvious.

## Guardian v1

Guardian contains **26 talents and 73 available ranks** across 11 WotLK rows. The first six rows contain 57 available ranks and are the build-complete core; the last five rows become progressively sparser.

### Rows 1–6

1. **Vitalidad 5**, **Consistencia 5**, **Fuerza descomunal 5**.
2. **Especialización con escudo 5**, **Cicatrización 2**, **Desvío 3**.
3. **Impactos dolorosos 3**, **Contestación 1**, **Impasibilidad 2**.
4. **Bloqueo crítico 3**, **Última Carga 1**, **Desvío de hechizos 3**, **Especialización en armas de una mano 5**.
5. **Paso firme 2**, **Superviviente 3**, **Ventaja desleal 2**.
6. **Indomable 3**, **Aclimatación 3**, **Golpes de barrido 1**.

The opening rows stay generic. By rows 5–6 the player can complete very different defensive identities: shield/block, avoidance and counterattack, raw-health survival, magic adaptation, or hybrids such as an evasive rogue-like tank.

Important Adventurer customizations:

- **Vitalidad** gives +2% maximum health per rank, +10% at 5/5.
- **Consistencia** is armor-type aware: each rank adds 4% of cloth/leather item armor, 3% of mail item armor and 2% of plate item armor. Shields are excluded. The runtime script recalculates this from equipped effective item armor so the DBC marker itself does not apply a generic armor multiplier.
- **Impactos dolorosos** adds 5/10/15% threat only to Physical attacks and abilities and uses the stock `ability_backstab` icon.
- **Especialización con escudo** reuses the native WotLK Warrior rank spells so the original +1% block per rank and 20% per-rank chance to generate 5 Rage on block/dodge/parry remain intact.
- **Bloqueo crítico** keeps the 20/40/60% double-block mechanic but removes the Shield Slam-specific critical-strike rider.
- **Indomable** keeps Survival of the Fittest's +2/4/6% attributes and -2/4/6% melee critical-hit chance taken while removing the Bear-only armor rider.
- **Superviviente** is Ardent Defender renamed and intentionally reuses its native script-sensitive ranks.
- **Ventaja desleal** intentionally reuses the native proc-sensitive ranks.

### Rows 7–11

7. **Nervios de acero 2**, **Oración 2**, **Ira enfocada 3**.
8. **Baluarte 3**.
9. **Escudo de daño 2**.
10. **Máquina de demolición 3** — 25/50/75% proc chance on block/parry/dodge for the existing +5% Physical damage Enrage.
11. **Arrojar escudo 1**.

The deep shield chain is optional. A non-shield Guardian is expected to be functional well before it and can spend the remaining level-60 points in another tree. `Arrojar escudo` remains Guardian definition index 24 so its custom spell ID stays stable at **290240**.

## Champion v0

Champion contains **28 talents and 80 total ranks** across 11 tiers. Its current implementation deliberately mixes WotLK physical systems that normally belong to different classes: dual wielding, two-handed weapons, daggers and fist weapons, poisons, stealth, combo points, Rage, Energy and hybrid attack-power/spell-power interactions.

Where a native mechanic is safe and script-sensitive, Champion may reuse the Blizzard spell rows. Mechanics whose original spell-family, stance or resource restrictions would bind them to another class are cloned and sanitized. Champion also supports Adventurer-owned triggered child spells so proc talents can keep their event logic while applying custom generic buffs.

The runtime test covers native talent infrastructure as well as the authored mechanics: all tabs must render, points must spend correctly, generated ranks must learn the intended spell IDs, prerequisite arrows must match the authored trees, and selections must survive logout/login. Source mechanics that prove class-, stance-, form-, resource-, or spell-family-dependent are replaced or sanitized after real-client smoke testing.
