# Adventurer talents

Adventurer currently authors native WotLK talent tabs through generated Talent/Spell DBC rows:

- **Guardian** / **Guardián** — tanking, mitigation and survival.
- **Champion** / **Campeón** — physical and hybrid melee damage. Conceptually this tree is evolving toward **Mercenary / Mercenario**.
- **Scholar** / **Erudito** — magic damage and healing. Reserved in the current client pass.

Each authored tree has its own JSON spec and its own Adventurer-owned Talent/Spell ID range. Guardian keeps the original `5000` / `290000` ranges; Champion uses `6000` / `300000`. Adding another tree must never reindex an externally stable Adventurer spell ID.

## Build-depth rule

Talent trees are designed around viable builds rather than around filler.

- level 60: 51 points; 31/20, 30/21 and comparable hybrids must work;
- level 70: 61 points;
- level 80: 71 points;
- roughly 10 points is a dip, 20 points is a functional secondary package, and 30 points should already provide a complete tree identity;
- 40+ points are advanced specialization and the deepest rows are optional specialization/capstone territory.

A tree may contain 80 available ranks when every slot is intentional; the number itself is not a target. Weak filler and mandatory corridors are still avoided. Adventurer trees use **two deepest-row ultimates** so different versions of the same broad archetype can finish in distinct ways.

## Guardian final layout

Guardian contains **32 talents and 80 available ranks** across 11 WotLK rows. Rows 1–6 contain 53 available ranks and form the level-60 build core. The deep half then branches into shield defense, avoidance/reactive defense, heavy weapons and group protection rather than becoming one mandatory corridor.

### Rows 1–6

1. **Vitalidad 5**, **Consistencia 5**, **Fuerza descomunal 1**.
2. **Especialización con escudo 5**, **Cicatrización 2**, **Desvío 3**.
3. **Impactos dolorosos 3**, **Contestación 1**, **Impasibilidad 2**.
4. **Bloqueo crítico 3**, **Última Carga 1**, **Desvío de hechizos 3**, **Especialización en armas de una mano 5**.
5. **Paso firme 2**, **Superviviente 3**, **Ventaja desleal 2**.
6. **Armado hasta los dientes 3**, **Aclimatación 3**, **Golpes de barrido 1**.

The opening rows stay generic. By rows 5–6 the player can complete very different defensive identities: shield/block, avoidance and counterattack, raw-health survival, magic adaptation, armor scaling, or hybrids such as an evasive rogue-like tank.

Important Adventurer customizations:

- **Vitalidad** gives +2/4/6/8/10% maximum health and uses `spell_nature_abolishmagic`.
- **Consistencia** is armor-type aware: each rank adds 4% of cloth/leather item armor, 3% of mail item armor and 2% of plate item armor. Shields are excluded. The runtime script recalculates this from equipped effective item armor so the DBC marker itself does not apply a generic armor multiplier.
- **Fuerza descomunal** is now a single 1/1 foundation talent that grants +15% total Strength and uses `inv_gauntlets_19`.
- **Cicatrización** gives +3/6% healing received and uses `spell_shadow_lifedrain`.
- **Impactos dolorosos** adds 5/10/15% threat only to Physical attacks and abilities and uses `ability_backstab`.
- **Especialización con escudo** reuses the native WotLK Warrior rank spells so the original +1% block per rank and 20%-per-rank chance to generate 5 Rage on block/dodge/parry remain intact.
- **Bloqueo crítico** keeps the 20/40/60% double-block mechanic but removes the Shield Slam-specific critical-strike rider.
- **Superviviente** clones the three Ardent Defender rank rows as Adventurer-owned spells `290150`–`290152`, uses `spell_misc_emotionangry`, and is bound by the versioned world update to AzerothCore's proven `spell_pal_ardent_defender` runtime script.
- **Ventaja desleal** intentionally reuses the native proc-sensitive ranks.
- **Armado hasta los dientes** is Adventurer's buffed adaptation of the WotLK talent: +2/4/6 Attack Power per 150 final Armor. Its custom rank markers are `290260`–`290262`; the runtime AP hook uses the final armor value, so it naturally synergizes with Consistencia and temporary armor buffs without inheriting Warrior-only spell-family data.

### Rows 7–11

7. **Oración 2**, **Ira enfocada 2**, **Nervios de acero 2**.
8. **Baluarte 3**, **Indomable 3**, **Arremetida de conmoción 1**.
9. **Escudo de daño 2**, **Máquina de demolición 3**, **Empuñadura de titán 1**.
10. **Atracarse de sangre 5**, **Vigilancia 1**.
11. **Arrojar escudo 1**, **Ola de choque 1**.

Deep Guardian deliberately supports several fantasies at once:

- the shield lane is **Baluarte -> Escudo de daño -> Arrojar escudo**;
- the group/control lane is **Arremetida de conmoción -> Vigilancia**;
- the heavy-weapon lane is **Empuñadura de titán -> Ola de choque**;
- **Indomable**, **Máquina de demolición** and **Atracarse de sangre** remain useful to avoidance/reactive and hybrid Guardians without forcing a shield.

The approved prerequisite arrows are exactly:

- Desvío -> Contestación;
- Especialización con escudo -> Bloqueo crítico;
- Especialización en armas de una mano -> Golpes de barrido;
- Baluarte -> Escudo de daño -> Arrojar escudo;
- Arremetida de conmoción -> Vigilancia;
- Empuñadura de titán -> Ola de choque.

Deep WotLK mechanics are adapted conservatively:

- **Arremetida de conmoción**, **Empuñadura de titán**, **Vigilancia** and **Ola de choque** reuse their native WotLK spell rows so AzerothCore's proven stun/AP, Titan Grip, threat-transfer and cone/stun behavior stays intact.
- **Atracarse de sangre** cannot safely reuse the DK child auras because their spell-family masks only affect DK attacks. Guardian therefore owns custom ranks `290290`–`290294`: armor penetration is always active at 2/4/6/8/10%, while the matching all-damage bonus is enabled only above 75% health by the Adventurer runtime.
- **Máquina de demolición** remains the custom 25/50/75% proc on block/parry/dodge for +5% Physical damage for 12 sec.
- **Arrojar escudo** remains Guardian definition index 24 so its custom spell ID stays stable at **290240**. Its approved icon is `inv_jewelry_trinketpvp_02`.

Guardian's two row-11 ultimates are therefore **Arrojar escudo** and **Ola de choque**.

## Champion v0

Champion contains **28 talents and 80 total ranks** across 11 tiers. Its current implementation deliberately mixes WotLK physical systems that normally belong to different classes: dual wielding, two-handed weapons, daggers and fist weapons, poisons, stealth, combo points, Rage, Energy and hybrid attack-power/spell-power interactions.

Where a native mechanic is safe and script-sensitive, Champion may reuse the Blizzard spell rows. Mechanics whose original spell-family, stance or resource restrictions would bind them to another class are cloned and sanitized. Champion also supports Adventurer-owned triggered child spells so proc talents can keep their event logic while applying custom generic buffs.

The runtime test covers native talent infrastructure as well as the authored mechanics: all tabs must render, points must spend correctly, generated ranks must learn the intended spell IDs, prerequisite arrows must match the authored trees, and selections must survive logout/login. Source mechanics that prove class-, stance-, form-, resource-, or spell-family-dependent are replaced or sanitized after real-client smoke testing.
