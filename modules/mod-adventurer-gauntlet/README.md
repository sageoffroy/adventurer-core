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

- `AdventurerGauntlet.cpp` — orquestacion principal de gameplay: inicio, transicion entre mazmorras, bosses y Khadgar. No contiene SQL de persistencia.
- `RunProgress.h/.cpp` — unica frontera de persistencia de las companias/runs: crea la run, guarda dungeon/checkpoint, integrantes, caidas y posiciones de reanudacion.
- `RunReconnect.cpp` — politica de reconexion. Consulta `RunProgress` y decide donde reubicar al personaje; no accede directamente a la base.
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

### Selector aleatorio temporal por expansion

Mientras se define el futuro mapa de rutas, Khadgar ofrece tres accesos de prueba:

- **Mazmorra clasica aleatoria**.
- **Mazmorra de Terrallende aleatoria**.
- **Mazmorra de Rasganorte aleatoria**.

Cada opcion elige al azar una mazmorra del pool correspondiente y usa el flujo real de Gauntlet: validacion de grupo, compania persistente, binding/reconexion, nivel de run y escalado por jugadores presentes.

Los pools temporales viven encapsulados en `DungeonCatalog.h/.cpp`. Ese catalogo es tambien la fuente de nombre, map ID y coordenadas de entrada para los mapas soportados. El objetivo es comparar rapidamente como responde el escalado a contenido Classic, TBC y WotLK antes de construir el mapa definitivo de rutas.

Pools actuales:

- Classic: Sima Ignea, Minas de la Muerte, Las Mazmorras de Ventormenta, Castillo de Colmillo Oscuro y Cementerio del Monasterio Escarlata.
- Terrallende: Murallas del Fuego Infernal, Horno de Sangre, Recinto de los Esclavos y Tumbas de Mana.
- Rasganorte: Azjol-Nerub, Fortaleza de Utgarde, El Nexo y Gundrak.

Estas opciones son temporales y no representan todavia la progresion geografica final.

### Escalado dinamico por jugadores presentes

La dificultad de la instancia usa la cantidad de Aventureros del Gauntlet **fisicamente presentes en la dungeon**, no el numero total de integrantes del grupo fuera del mapa.

Cuando aumenta esa cantidad, `GauntletScaling.cpp` reajusta solamente criaturas vivas que esten **fuera de combate**. Una criatura que ya esta peleando conserva el tamano de grupo con el que comenzo ese combate, tanto para vida como para dano. Al morir se descarta su estado de escalado.

La dificultad de una instancia **nunca baja** durante esa instancia. Se conserva el mayor numero de Aventureros que llego a estar presente. Si una compania entra con 3 y uno muere, se desconecta o abandona la dungeon, los encuentros pendientes siguen escalados para 3. Si despues entra un cuarto, la dificultad puede subir a 4, pero nunca volver a 3 mientras esa instancia exista.

Cada criatura conserva internamente su vida maxima base y el ultimo tamano de grupo aplicado. Los cambios 2→3, 3→4, etc. siempre se calculan desde esa base para evitar multiplicar escalados sucesivos entre si.

Esto permite que un nuevo miembro llegue a la misma instancia usando el flujo normal de grupo de WoW: al aparecer fisicamente en la dungeon, los encuentros que todavia no comenzaron se adaptan al nuevo numero de jugadores sin alterar el combate que ya este en curso.

## Persistencia de companias y reanudacion

La run es una entidad persistente de **compania**, no una coleccion de variables temporales del worldserver.

Fuente de verdad en la base `characters`:

- `adventurer_gauntlet_runs` — una fila por expedicion. Guarda nombre, lider, tamano inicial del grupo, nivel base, dungeon actual, checkpoint, mejor dungeon alcanzada, estado y fechas.
- `adventurer_gauntlet_run_members` — integrantes de cada expedicion, posicion exterior de retorno, ultima posicion guardada en dungeon y estado de caida.

Regla de encapsulamiento:

```text
AdventurerGauntlet.cpp  ----\
                         > RunProgress.h/.cpp ---> CharacterDatabase
RunReconnect.cpp       ----/
```

Ningun otro archivo de gameplay debe escribir directamente estas tablas. Si aparece un nuevo dato persistente de la run, se agrega primero a la API de `RunProgress` y luego se consume desde el gameplay.

Flujo actual:

1. Khadgar inicia la expedicion: `RunProgress::StartRun` crea la compania y sus integrantes. `party_size` representa el tamano inicial y no cambia por desconexiones posteriores.
2. Al cambiar de dungeon: `RunProgress::AdvanceDungeon` actualiza dungeon/mapa, reinicia el checkpoint local y conserva la mejor dungeon alcanzada.
3. Al matar bosses/checkpoints: `RunProgress::SaveCheckpoint` guarda el progreso significativo.
4. Al desconectar dentro de una dungeon: `RunProgress::SaveLogoutPosition` guarda la ultima posicion.
5. Al reconectar: `RunReconnect.cpp` usa `RunProgress::LoadResumePoint`. Si la ultima posicion pertenece a la dungeon actual, intenta volver alli; si no, usa la entrada segura de esa dungeon.
6. Al morir: `RunProgress::MarkMemberFallen` marca al integrante y, cuando ya no quedan supervivientes, la compania queda `fallen`.
7. Si un integrante comienza otra expedicion mientras una anterior figura activa, la anterior pasa a `abandoned`.

Estados de una run:

- `active` — expedicion vigente y reanudable.
- `fallen` — la compania termino por muerte.
- `completed` — reservado para completar todo el recorrido Gauntlet.
- `abandoned` — sustituida por una nueva expedicion.

### Que se guarda y que no

Se guarda el **progreso roguelike significativo**: compania, integrantes, tamano de grupo, nivel, dungeon, checkpoint, mejor marca y posicion de reanudacion.

No se promete persistir el estado byte a byte de una instancia de AzerothCore. Mobs comunes, puertas o scripts internos deben restaurarse a partir de checkpoints cuando cada dungeon implemente su restauracion. Esta separacion evita acoplar el historial/ranking a los IDs efimeros de instancia.

Esta misma tabla de runs es la fuente prevista para el futuro **tablero de companias**. El ranking debe leer historial persistente; no debe reconstruirse desde memoria del worldserver.

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
