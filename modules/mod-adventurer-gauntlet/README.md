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

### Selector de mazmorra especifica

Para depuracion, Khadgar ofrece **Elegir mazmorra especifica**. El submenu separa Classic, Terrallende y Rasganorte y permite entrar directamente a cualquiera de las mazmorras habilitadas en los pools temporales.

La entrada especifica usa exactamente el mismo flujo Gauntlet que la seleccion aleatoria: validacion de grupo, compania persistente, nivel de run, binding/reconexion y escalado. No es un teleport GM aislado; sirve para reproducir bugs de una dungeon concreta tantas veces como sea necesario.

### Primera campana: La sombra sobre Ventormenta

Ademas de los tres selectores aleatorios de prueba, Khadgar ofrece una cuarta opcion fija: **La sombra sobre Ventormenta**.

Es la primera campana completa usada como patron para el futuro sistema de expediciones:

1. **Minas de la Muerte** — Edwin VanCleef (entry 639).
2. **Las Mazmorras de Ventormenta** — Bazil Thredd (entry 1716).
3. **Profundidades de Roca Negra** — Emperador Dagran Thaurissan (entry 9019).
4. **Guarida de Onyxia** — Onyxia (entry 10184).

La campana se identifica persistentemente con `campaign_key=stormwind_shadow`. El stage actual sigue usando `current_dungeon`, por lo que reconectar o reiniciar el servidor conserva tanto la campana como la etapa.

Al morir el jefe objetivo de cada etapa, Khadgar aparece junto al cuerpo, presenta de forma provisional la pista narrativa obtenida de los ultimos recuerdos del jefe y permite al lider continuar. Antes de abrir el siguiente portal, `RunProgress::AdvanceDungeon` persiste el nuevo stage/mapa. Al caer Onyxia, la run pasa a estado `completed`.

La definicion narrativa y los bosses de la campana viven en `CampaignCatalog.h/.cpp`. Las coordenadas y datos de mapas siguen perteneciendo a `DungeonCatalog.h/.cpp`. Los textos actuales son funcionales/provisionales: la redaccion final de Khadgar se pulira despues sin cambiar el flujo tecnico.

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

### Normalizacion de nivel por mazmorra

El nivel nativo ya no se deduce buscando la criatura de menor nivel de todo el mapa. Cada entrada de `DungeonCatalog` declara un `NativeBaseLevel` propio y el nivel Gauntlet conserva solamente la diferencia interna respecto de esa base:

```text
nivel Gauntlet del mob = nivel de la run + max(0, nivel nativo del mob - NativeBaseLevel)
```

Esto evita que NPC auxiliares, criaturas de otras zonas del mismo map o mapas compartidos distorsionen toda la instancia. Es especialmente importante para **Monasterio Escarlata**, donde Cementerio, Biblioteca, Armeria y Catedral comparten el map 189. Por ahora el catalogo habilita solo Cementerio y usa su base propia; cuando se incorporen las otras alas deberan modelarse como stages/dungeons independientes aunque compartan `map_id`.

Las bases actuales son parametros de balance del Gauntlet y se ajustaran con pruebas en juego; no se recalculan dinamicamente desde los spawns del mapa. En Cementerio del Monasterio Escarlata la base se fija en 30 para reducir en dos niveles el resultado respecto de la primera prueba con base 28.

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


## Joining an active company

When a player without an active Gauntlet run talks to Khadgar while grouped with an online party member who is already inside that party's active Gauntlet instance, Khadgar replaces the normal start/testing menu with a single option to join that company.

Joining does not require party leadership. The new member is persisted into the existing run, keeps the run's stable base level/campaign stage/checkpoint, and enters at the current dungeon entrance. The existing party and instance are not reset. Late joins retain the current +/-5 level compatibility rule and the run remains capped at five living members.


### Knowledge loot

Knowledge is an independent auxiliary Gauntlet roll, separate from equipment,
potions, ammunition, bags and SpellDraft currency scrolls.

- Chance: **2.00% per eligible creature**.
- A successful roll adds exactly one knowledge item.
- Eligible catalog: custom entries `910240..910599` that exist in
  `item_template`.
- Level window: `RequiredLevel <= rewardLevel + 3`. This allows a book to drop
  slightly before it can be read, while its item-level requirement still blocks
  early use.
- Selection among eligible knowledge items is uniform.
- The implementation is isolated in `KnowledgeRewards.cpp/.h`; curated boss
  and trash loot only call `KnowledgeRewards::TryAddDrop`.

The knowledge catalog itself is owned by SpellDraft at
`config/spelldraft/knowledge_books.csv`. Normal ability books supplement the
active-card draft; active-talent tomes are their exclusive acquisition path.
