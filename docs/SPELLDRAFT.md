# SpellDraft — current model

This document describes the current SpellDraft behavior in this branch. It supersedes older version-specific design notes.

## Core idea

The card is the unit of progression. A card can grant one spell, several related spells, or one rank in a passive/talent chain.

SpellDraft is the progression system for the native Adventurer class. Talents are obtained as SpellDraft cards rather than through a fixed native talent tree.

## Card data

Packaged card data lives in `config/spelldraft/cards.csv`.

The catalogue contains fields for card identity, type, source level, rarity, weight, rank grants, prerequisites/unlocks and display metadata.

Related metadata lives in `config/spelldraft/catalog_metadata.csv` and subclass presentation data lives in `config/spelldraft/subclasses.json`.

## Card types

- Active cards grant active abilities or active bundles.
- Talent cards grant passive/talent ranks and may progress through several spell IDs.

Active spell families rank automatically when the underlying spell family has later ranks and the character reaches the relevant level. Talent ranks are separate SpellDraft choices.

## Rarity and weight

Rarity and weight are separate concepts. Rarity controls the general draw difficulty of a quality; weight controls how strongly an eligible card competes with other eligible cards.

The runtime combines the configured values during weighted selection.

## Eligibility graph

Cards are filtered server-side before an offer is generated. A card can require another card or a minimum owned rank. Selecting a card can unlock other active or talent cards.

Dependent cards are not automatically granted unless a card explicitly bundles multiple spell grants.

## Progression

The current progression model queues active and talent picks independently. Level transitions can queue multiple unresolved picks, and unresolved offers persist across relog.

The runtime is authoritative: the client displays offers but does not decide eligibility or ownership.

## Meta mechanics

SpellDraft uses three persistent meta currencies:

- Reroll: redraw the unresolved offer. Characters start with **3**.
- Bless: increase the future draw weight of one eligible displayed card. Characters start with **1**.
- Destroy: permanently exclude one eligible card from that character's pool. Characters start with **1**.

None of these currencies are regenerated automatically by leveling. Additional charges are intended to come from special Gauntlet loot. There is currently no configured accumulation cap; drop rates are the balancing control. Balance/settings live in `config/spelldraft/spelldraft.conf`.

Gauntlet drops three tradeable, single-use SpellDraft currency scrolls through an independent **1%** auxiliary roll:

- **Scroll de Suerte** (`910237`, `INV_Scroll_11`): +1 Reroll.
- **Scroll de Bendición** (`910238`, `INV_Scroll_15`): +1 Bless.
- **Scroll del Olvido** (`910239`, `INV_Scroll_16`): +1 Destroy.

On a successful scroll roll, the distribution is **50% / 25% / 25%** respectively. The scroll is consumed on use, the new charge is persisted immediately, and the SpellDraft counters are refreshed. This roll is independent from equipment, ammo, potion, stock-scroll and bag rolls.

## Persistence

Per-character draft state is stored through the existing Adventurer SpellDraft persistence path. It includes owned card ranks, unresolved offer state and current meta-mechanic state/charges.

Existing schema/state is migrated by the current runtime when required; do not create a parallel persistence system for a feature.

## Runtime files

Packaged runtime seeds:

```text
config/spelldraft/cards.csv
config/spelldraft/spelldraft.conf
```

The install/update pipeline places editable runtime copies beside the AzerothCore data directory and maintains packaged defaults where the existing tooling supports `.dist` files. Normal catalogue/balance changes are designed to be data-driven rather than requiring a worldserver recompile.

## Server/client flow

```text
cards.csv + spelldraft.conf + metadata
  -> tools/spelldraft_runtime.py / generation helpers
  -> Adventurer server runtime
  -> per-character persisted state
  -> Adventurer addon protocol
  -> client/AdventurerDraftMeta.lua
  -> player chooses an offered card/meta action
  -> server validates and updates state/grants
```

## Presentation subclasses

SpellDraft uses four presentation families for organization/UI:

- Mercenario
- Explorador
- Hechicero
- Iluminado

They are presentation/organization metadata, not fixed talent trees.

## Source of truth rule

For current behavior, use this file plus repository code/config. `docs/spelldraft-v1.md` and `docs/spelldraft-meta-v2.md` are historical design records and must not override current implementation.


## Libros y tomos de conocimiento

El loot de conocimiento complementa SpellDraft; no reemplaza el draft de habilidades.

Fuente de verdad: `config/spelldraft/knowledge_books.csv`.

### Habilidades normales

Las habilidades activas de `cards.csv` conservan sus dos vías de adquisición:

1. pueden aparecer normalmente como cartas de SpellDraft;
2. pueden aprenderse mediante libros encontrados como loot.

Cada habilidad activa tiene un libro específico. Su entry se mantiene estable como
`910300 + card_id`; por ejemplo, la card 14 (Golpe siniestro) usa el item
`910314`, **Manual del Golpe siniestro**.

También existen libros aleatorios:

- `910240` **Tomo perdido**: habilidad aleatoria de cualquier clase;
- `910241..910249`: un libro aleatorio por clase, con la nomenclatura
  Manual/Libro/Escrito/Tratado/Códice/Tablilla/Grimorio.

Los libros aleatorios solo pueden elegir habilidades que el Aventurero todavía
no conozca, cuyo `source_level` ya haya alcanzado y cuyos prerrequisitos de
SpellDraft estén cumplidos. Si no existe ninguna opción válida, el libro no se
consume.

Aprender una habilidad mediante libro registra la card como poseída en el mismo
estado persistente de SpellDraft. Por eso deja de aparecer como adquisición
nueva en futuras ofertas y continúa subiendo de rango con la lógica normal al
subir de nivel.

### Talentos activos

Los talentos activos son exclusivos de tomos. Todo spell listado como
`kind=active_talent` en `knowledge_books.csv` se excluye del catálogo de
talentos generado en runtime, incluso si aparece como talento sintético derivado
de `catalog_metadata.csv`.

Catálogo inicial:

- Árbol de Vida (33891), nivel 50;
- Mordedura de hielo / Cold Snap (11958), nivel 30;
- Sangre fría (14177), nivel 30;
- Preparación (14185), nivel 30;
- Presteza de la Naturaleza, druida (17116), nivel 30;
- Dominación vil (18708), nivel 20;
- Favor divino (20216), nivel 20;
- Vigilancia (50720), nivel 40;
- Danza de las Sombras (51713), nivel 60.

Si el personaje ya conoce el conocimiento contenido en un libro/tomo, el objeto
no se consume.

### Objetos y uso

Los scrolls de moneda SpellDraft y los libros/tomos comparten el spell técnico
`920900` únicamente para que el cliente 3.3.5a presente el objeto como usable.
Ese spell no concede ningún efecto: la acción real vive en los respectivos
`ItemScript` del core. Así evitamos heredar efectos stock accidentales de los
objetos usados como base visual.

Los libros son comerciables, apilables hasta 20 y respetan `RequiredLevel`.
Los específicos y los tomos de talento pueden caer hasta tres niveles antes de
poder usarse; el jugador puede guardarlos hasta alcanzar el requisito.
