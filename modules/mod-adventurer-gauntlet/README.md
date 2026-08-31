# mod-adventurer-gauntlet

Modulo Gauntlet / Dungeon Master de Aventureros de Azeroth.

Gauntlet se monta sobre la base estable de Aventurero + SpellDraft. Para la linea actual:

```text
stable/spelldraft-v3
  = Aventurero + SpellDraft v3 + pack de iconos administrado

stable/gauntlet-v3
  = SpellDraft v3 + este modulo
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
- `Lobo solitario` (`910501`) identifica al aventurero que entra solo a las mazmorras controladas por el modo. En la primera version v3 es un aura visible sin bonus de balance inventado.
- El Libro de Objetos registra por cuenta cada objeto custom actual descubierto al lootearlo; la muerte o eliminacion del personaje no borra ese descubrimiento.
- Los items y sets curados son propios del modulo y no deben mezclarse con la logica de SpellDraft.

## Estructura

### `src/`

- `AdventurerGauntlet.cpp` — orquestacion principal de la run y comportamiento general del modo.
- `GauntletScaling.cpp` — escalado de criaturas/grupo.
- `GauntletPermadeath.cpp` — muerte/permadeath de la run.
- `LoneWolf.cpp` — aura de reconocimiento para runs en solitario.
- `CuratedRewards.cpp` — seleccion y escritura de recompensas controladas en bosses.
- `AccountStash.cpp` — stash persistente de cuenta.
- `AccountCollection.cpp` — descubrimientos persistentes del Libro de Objetos por cuenta.
- `SetBonuses.cpp` — bonus de sets custom.
- `KhadgarCelebration.cpp` — comportamiento/presentacion relacionado con Khadgar.
- `loader.h` — registro de scripts del modulo.

### `data/items/`

- `early_items.csv` — catalogo de objetos custom/curados.
- `sets.csv` — definiciones de sets y sus bonus.

### `data/sql/`

Actualizaciones de base de datos propiedad de Gauntlet, incluidos stash y Libro de Objetos. No moverlas al SQL base de SpellDraft salvo que realmente dejen de ser especificas del modulo.

## Libro de Objetos

El libro es una coleccion de descubrimientos de cuenta, no un banco.

Actualmente registra:

- objetos custom del Aventurero en `910200-910224` cuando existen y son looteados;
- recompensas custom Gauntlet en `911100-911399`.

Solo los objetos descubiertos son enviados al cliente. Los no descubiertos no se muestran. El descubrimiento queda guardado en `adventurer_gauntlet_account_collection` por `account_id + item_entry`.

Se abre con:

```text
/objetos
/librodeobjetos
```

El Baul de Expediciones sigue siendo el sistema separado que conserva objetos fisicos.

## Catalogo de objetos

La fuente de verdad de recompensas Gauntlet es:

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

## Integracion con SpellDraft v3

La logica de gameplay del Gauntlet permanece dentro de `modules/mod-adventurer-gauntlet/` y `tools/khadgar_gauntlet/`.

Los puntos tecnicos compartidos con la base son datos que deben terminar en el mismo cliente/servidor:

- `tools/sync_item_dbc.py` sincroniza metadata de objetos custom;
- `tools/gauntlet_spells.py` define Juramento (`910500`) y Lobo solitario (`910501`), que el adaptador v3 incorpora al mismo `Spell.dbc` usado por servidor y cliente;
- si `client/icons/` contiene `lobo_solitario.blp` y se regenera `client/icons/catalog.csv`, Lobo solitario usa ese nuevo icono automaticamente.

No mover gameplay de Gauntlet a archivos de SpellDraft solo para evitar estos puntos de integracion.

## Instalacion

Usar la rama estable actual:

```bash
cd ~/adventurer-core

git fetch origin
git switch stable/gauntlet-v3
git reset --hard origin/stable/gauntlet-v3
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
CORE_DIR=~/aventurerosdeazeroth \
SERVER_DATA_DIR=~/aventurerosdeazeroth/env/dist/data \
CLIENT_DIR="/mnt/c/Games/World of Warcraft 3.3.5a" \
  bash tools/khadgar_gauntlet/install.sh
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

- cambios solo de Gauntlet: `v3.1`, `v3.2`, etc.;
- cuando SpellDraft tenga una nueva version mayor estable, integrar esa base y continuar con el mismo numero mayor en Gauntlet;
- no volver a desarrollar desde `feature/khadgar-gauntlet-v1`, `feature/khadgar-gauntlet-v1-clientfix` ni desde el antiguo `aventurerosdeazeroth/feature/mod-dungeon-master`.

La documentacion general de esta relacion vive en `docs/GAUNTLET.md`.
