# mod-adventurer-gauntlet

Modulo Gauntlet / Dungeon Master de Aventureros de Azeroth.

Gauntlet se monta sobre la base estable de Aventurero + SpellDraft. Para la linea actual:

```text
stable/spelldraft-v2
  = Aventurero + SpellDraft v2

stable/gauntlet-v2
  = SpellDraft v2 + este modulo
```

Khadgar es parte de la experiencia, pero no define el alcance completo del modulo.

## Diseno actual

- Los personajes comienzan la run en nivel 1.
- Khadgar registra/inicia la experiencia de Gauntlet.
- La run usa mazmorras originales de WoW con reglas propias del modo.
- La muerte permanente de la run se implementa en `GauntletPermadeath.cpp`.
- El escalado propio del modo se implementa en `GauntletScaling.cpp`.
- Los mobs normales no son la fuente principal de recompensas del desafio.
- Los bosses/checkpoints usan recompensas controladas por Gauntlet.
- Las recompensas actuales de los bosses de Ragefire se escriben directamente en el loot del cuerpo del boss; no se usa un segundo Cofre de Expedicion para ese flujo.
- El sistema de stash de cuenta vive en `AccountStash.cpp` y su UI cliente asociada.
- Los items y sets curados son propios del modulo y no deben mezclarse con la logica de SpellDraft.

## Estructura

### `src/`

- `AdventurerGauntlet.cpp` — orquestacion principal de la run y comportamiento general del modo.
- `GauntletScaling.cpp` — escalado de criaturas/grupo.
- `GauntletPermadeath.cpp` — muerte/permadeath de la run.
- `CuratedRewards.cpp` — seleccion y escritura de recompensas controladas en bosses.
- `AccountStash.cpp` — stash persistente de cuenta.
- `SetBonuses.cpp` — bonus de sets custom.
- `KhadgarCelebration.cpp` — comportamiento/presentacion relacionado con Khadgar.
- `loader.h` — registro de scripts del modulo.

### `data/items/`

- `early_items.csv` — catalogo de objetos custom/curados.
- `sets.csv` — definiciones de sets y sus bonus.

### `data/sql/`

Actualizaciones de base de datos propiedad de Gauntlet. No moverlas al SQL base de SpellDraft salvo que realmente dejen de ser especificas del modulo.

## Catalogo de objetos

La fuente de verdad es:

`data/items/early_items.csv`

Cada fila crea un item custom dentro del rango reservado del Gauntlet clonando un item stock de WotLK. Esto permite reutilizar modelos, iconos, slots, sonidos, materiales y durabilidad.

Campos especiales:

- `source_entry`: item stock que sirve como base.
- `display_id`: opcional; fuerza un `ItemDisplayInfo` stock distinto al del `source_entry`.
- `set_key`: opcional; agrupa la pieza dentro de un set curado server-side.
- `equip_spell1` / `equip_spell2`: spells stock aplicados como efectos `Equip:` propios de esa pieza.
- stats, armor y dano pueden sobreescribirse sin cambiar el modelo.

Los efectos heredados del item fuente se limpian: un objeto nuevo solo conserva los efectos declarados explicitamente en el CSV.

## Sets curados

Los bonus estan en:

`data/items/sets.csv`

Formato:

`enabled;set_key;name;pieces_required;spell_id;description`

Una misma `set_key` puede tener varios umbrales, por ejemplo 2, 4 y 6 piezas. Los bonus se aplican server-side usando spells stock y se recalculan segun los hooks del modulo.

## Integracion con SpellDraft

La logica de gameplay del Gauntlet permanece dentro de `modules/mod-adventurer-gauntlet/` y `tools/khadgar_gauntlet/`.

El principal punto tecnico compartido con la base Aventurero/SpellDraft es el pipeline final de `Item.dbc`, incluido `tools/sync_item_dbc.py`, porque los items custom del Gauntlet deben existir tanto para worldserver como para el cliente.

No mover gameplay de Gauntlet a archivos de SpellDraft solo para evitar ese punto de integracion.

## Instalacion

Usar la rama estable actual:

```bash
cd ~/adventurer-core

git fetch origin
git switch stable/gauntlet-v2
git reset --hard origin/stable/gauntlet-v2
```

Primero actualizar la base Aventurero/SpellDraft instalada:

```bash
./update.sh \
  --core-dir ~/aventurerosdeazeroth \
  --server-data-dir ~/aventurerosdeazeroth/env/dist/data \
  --dbc-src ~/dbc-clean-esMX/dbc/esMX \
  --client-dir "/mnt/c/Games/World of Warcraft 3.3.5a" \
  --locale esMX
```

Despues instalar/actualizar el modulo Gauntlet:

```bash
CORE_DIR=~/aventurerosdeazeroth bash tools/khadgar_gauntlet/install.sh
```

Luego:

```bash
cd ~/aventurerosdeazeroth/build
make -j2
make install
```

Y arrancar:

```bash
cd ~/aventurerosdeazeroth/env/dist/bin
./worldserver
```

Durante desarrollo Khadgar puede spawnearse con:

```text
.npc add 910000
```

## Versionado

- cambios solo de Gauntlet: `v2.1`, `v2.2`, etc.;
- nueva base estable SpellDraft v3: integrar esa base y continuar como `stable/gauntlet-v3`;
- no volver a desarrollar desde `feature/khadgar-gauntlet-v1`, `feature/khadgar-gauntlet-v1-clientfix` ni desde el antiguo `aventurerosdeazeroth/feature/mod-dungeon-master`.

La documentacion general de esta relacion vive en `docs/GAUNTLET.md`.
