# Death Knight adaptations: approved design and open decisions

> Implementation snapshot for `feature/spelldraft-dk-adaptations-v1`, based on
> `stable/spelldraft-v1` at `291259fd48dd5f18bebc188e27387cd825a4cf67`.
> This document preserves the Spanish design conversation; it does not mean
> that the abilities are implemented or available in the runtime catalog.
> Later explicit decisions override earlier proposals. In particular, only
> ONE presence may be active; coexistence with stances remains allowed.
> Death Strike still needs its numeric level/combo table and launch details.
> Raise Dead remains provisional; the unused-combo resurrection is a note only.
> See `dk-adaptations-audit.md` for implementation boundaries and test gates.


Fecha: 2026-08-28. Documento de diseño, sin cambios aplicados al repositorio ni pruebas de balance en cliente.

## Decisiones

- Regla vigente de presencias: solo una activa entre Sangre, Escarcha y Profana; activar otra sustituye la anterior. Esta decisión posterior reemplaza la coexistencia previamente propuesta entre presencias. No cambia la coexistencia permitida entre una presencia y una actitud.

- Golpe sangriento: rareza RARO, disponible desde nivel 1; una carta con escalado, no 13 cartas.
- Ambos: 15 de ira, alcance cuerpo a cuerpo 5 yardas, daño físico, sin reutilización propia.
- Heroico: siguiente ataque automático, sin GCD, conserva amenaza adicional; magnitud de amenaza pendiente de comprobar en nuestro core.
- Sangriento: ataque instantáneo adicional, GCD 1,5 s, sin amenaza extra y sin generar poder rúnico.
- Sangriento conserva bonificación de 12,5% al daño total por cada enfermedad propia en el objetivo. No se ha aprobado sustituir enfermedades por sangrados.
- Actitud de batalla y Presencia de sangre pueden coexistir. Diseño inicial nivel 1: Batalla gratis, 10% penetración; Presencia gratis, +5% daño y curación del 4% del daño no periódico; pendiente verificar redondeo de curación.

## Curva corregida: anclas originales de Sangriento

Se descarta la regla de dos tercios de Heroico y la tabla anterior. Se conserva 40% de daño de arma normalizado y el adicional original en cada nivel nativo. Se añaden las anclas custom acordadas de nivel 1 y 8, y se interpola linealmente entre anclas. Es una adaptación normalizada: los valores intermedios no son rangos originales ni una reproducción por escalones del WoW original. No se garantiza idéntico DPS al cambiar runas por ira.

| Nivel | Adicional efectivo | Origen |
|---:|---:|---|
| 1 | +7 | Custom acordado |
| 8 | +14 | Custom acordado |
| 55 | +104 | [Original 45902](https://www.wowhead.com/wotlk/spell=45902/blood-strike) |
| 59 | +118 | [Original 49926](https://www.wowhead.com/wotlk/spell=49926/blood-strike) |
| 64 | +138,8 | [Original 49927](https://www.wowhead.com/wotlk/spell=49927/blood-strike) |
| 69 | +164,4 | [Original 49928](https://www.wowhead.com/wotlk/spell=49928/blood-strike) |
| 74 | +250 | [Original 49929](https://www.wowhead.com/wotlk/spell=49929/blood-strike) |
| 80 | +305,6 | [Original 49930](https://www.wowhead.com/wotlk/spell=49930/blood-strike) |

Los adicionales son posteriores al multiplicador de 40%: no multiplicarlos otra vez por 0,4. La implementación debe respetar la normalización de arma original y validar el orden de efectos. Se mantienen decimales de anclas para evitar errores acumulados; la tabla comparativa muestra dos decimales como máximo.

## Comparación en los 13 niveles de Heroico, más el cierre a 80

Estos niveles son puntos de consulta de la curva; no reemplazan sus anclas nativas. Heroico conserva sus valores originales, amenaza adicional y bonus Dazed; no se cambia su rareza. Sangriento es RARO, sin multiplicador extra por rareza. El daño de Sangriento se muestra sin enfermedades.

| Rango Heroico | Nivel | ID Heroico / fuente | Adicional Heroico | Extra contra Dazed, tooltip redondeado | Sangriento corregido |
|---:|---:|---|---:|---:|---|
| 1 | 1 | [78](https://www.wowhead.com/wotlk/spell=78/heroic-strike) | +11 | — | 40% de arma +7 |
| 2 | 8 | [284](https://www.wowhead.com/wotlk/spell=284/heroic-strike) | +21 | — | 40% de arma +14 |
| 3 | 16 | [285](https://www.wowhead.com/wotlk/spell=285/heroic-strike) | +32 | — | 40% de arma +29,32 |
| 4 | 24 | [1608](https://www.wowhead.com/wotlk/spell=1608/heroic-strike) | +44 | — | 40% de arma +44,64 |
| 5 | 32 | [11564](https://www.wowhead.com/wotlk/spell=11564/heroic-strike) | +60 | — | 40% de arma +59,96 |
| 6 | 40 | [11565](https://www.wowhead.com/wotlk/spell=11565/heroic-strike) | +93 | — | 40% de arma +75,28 |
| 7 | 48 | [11566](https://www.wowhead.com/wotlk/spell=11566/heroic-strike) | +136 | — | 40% de arma +90,6 |
| 8 | 56 | [11567](https://www.wowhead.com/wotlk/spell=11567/heroic-strike) | +178 | — | 40% de arma +107,5 |
| 9 | 60 | [25286](https://www.wowhead.com/wotlk/spell=25286/heroic-strike) | +201 | — | 40% de arma +122,16 |
| 10 | 66 | [29707](https://www.wowhead.com/wotlk/spell=29707/heroic-strike) | +234 | +82 | 40% de arma +149,04 |
| 11 | 70 | [30324](https://www.wowhead.com/wotlk/spell=30324/heroic-strike) | +317 | +111 | 40% de arma +181,52 |
| 12 | 72 | [47449](https://www.wowhead.com/wotlk/spell=47449/heroic-strike) | +432 | +151 | 40% de arma +215,76 |
| 13 | 76 | [47450](https://www.wowhead.com/wotlk/spell=47450/heroic-strike) | +495 | +173 | 40% de arma +268,53 |
| — | 80 | Cierre del escalado; no es un rango 14 de Heroico | +495 | +173 | 40% de arma +305,6 |

Heroico termina sus rangos en 76; Sangriento alcanza su última ancla original en 80. Por eso se descarta también congelar Sangriento a nivel 76.

## Ventajas para el balance

Heroico tiene amenaza adicional (útil para tanque), no usa GCD y a partir de nivel 66 gana daño contra Dazed. Dazed no equivale a cualquier ralentización ni a Stun. Sangriento es inmediato, no reemplaza el automático y tiene sinergia con enfermedades. En el comportamiento original Heroico reemplaza un automático que habría generado ira; Sangriento no lo reemplaza. Hay que comprobar estas interacciones en nuestro core.

## Corrección de la referencia original

Antes se citó +25 para el rango 1 original de Sangriento. La ficha WotLK de Wowhead informa 40% de arma +104 al nivel 55 y 12,5% por enfermedad propia: https://www.wowhead.com/wotlk/spell=45902/blood-strike . La corrección no cambia nuestras anclas custom +7 y +14.

## Pendiente de verificación

Daño y costo efectivo con armas de una y dos manos en cada tramo; normalización del daño de arma; amenaza exacta por rango de Heroico; acumulación de enfermedades admitidas por el script; coherencia tooltip/runtime; efectos de ambas posturas juntas. No se ha inspeccionado ni modificado el repositorio en este trabajo.



## Registro de decisiones posteriores

- Presencias y actitudes: sin rangos ni escalado, mismos porcentajes de nivel 1 a 80. Batalla y Sangre pueden coexistir. No imponer exclusión entre esas dos habilidades.
- Transfusión de sangre: consume toda la ira actual y recupera energía 1:1 hasta el máximo; el exceso se pierde. Sin manipular runas ni generar poder rúnico. Cierre: sin reutilización propia, GCD 1,5 s, no utilizable con 0 de ira, instantánea y sin rangos.
- Orden oscura: 10 de ira, ninguna actitud requerida, mismo efecto y reutilización que nuestro Provocar, sin rangos. Provocar se aprende con Actitud defensiva y mantiene el requisito nativo de actitud activa; Cargar conserva el requisito nativo de Actitud de batalla. No cambiar Provocar para implementar Orden oscura.

## Hervor de sangre: especificación numérica para implementar y probar

El usuario pide cerrar datos concretos antes de llevarlos a una rama. Esta sección sustituye el costo y daño pendientes: se fija como nuevo valor de diseño 20 de ira por lanzamiento, no una equivalencia nativa de runas a ira. Balance en juego no verificado.

- Disponible desde nivel 20; no ofrecer antes de ese nivel.
- Daño de Sombras instantáneo por objetivo en un radio de 10 yardas alrededor del personaje, GCD 1,5 s, sin reutilización propia y sin actitud requerida.
- Costo fijo: 20 de ira en todos los niveles. El costo se paga una vez por lanzamiento, no por objetivo. No generar poder rúnico ni gastar runas.
- Sin enfermedad propia válida: daño base de la tabla + 0,06 × poder de ataque.
- Con Peste de sangre o Fiebre de Escarcha propia: daño base + bonus fijo de la tabla + 0,09501 × poder de ataque. La tabla muestra la parte sin poder de ataque.
- El bonus se aplica una sola vez aunque haya ambas enfermedades; no las consume ni las propaga. Una enfermedad de otro jugador no habilita el bonus.
- No añadir penetración, amenaza plana extra, efecto de provocar ni ralentización. Mantener las reglas nativas de crítico, resistencias y modificadores de daño.
- El aporte original comprobado en AzerothCore upstream es 0,06 de PA; para enfermedad el core añade 95 y usa multiplicador 1,5835 sobre ese coeficiente (0,09501). Para el tramo bajo se reduce el bonus fijo, no los coeficientes de PA. No es un 50% más de daño ni un porcentaje por enfermedad.
- Rareza: no se asigna una nueva rareza en esta sección; la decisión explícita de RARO pertenece a Golpe sangriento.

### Cálculo de los rangos bajos

Datos base de Ventisca por tick, sin poder con hechizos ni escalado oculto: 20→25, 28→44, 36→65, 44→90, 52→117, 60→149. Son 8 ticks, de modo que los totales son 200, 352, 520, 720, 936 y 1192. El tooltip web puede mostrar valores a nivel 80; se toman los valores base del efecto.

Para usar la curva normalizada de referencia en 58 se interpola: 936 + (1192−936)×6/8 = 1128. Este 1128 es una referencia interpolada, NO un rango original de Ventisca.

Para niveles 20/28/36/44/52, multiplicar (89 mínimo, 107 máximo, 95 bonus por enfermedad) por VentiscaBase(nivel)/1128. Redondear al entero más cercano, mitades hacia arriba. Los resultados son las anclas inferiores de la tabla siguiente. A partir de 58 se conservan las cuatro anclas originales de Hervor.

### Rangos / anclas definitivos de esta versión de diseño

| Ancla | Nivel | Base | Bonus fijo por enfermedad | Base con enfermedad, sin PA | Origen |
|---:|---:|---|---:|---|---|
| 1 | 20 | 16–19 | +17 | 33–36 | Adaptado por proporción |
| 2 | 28 | 28–33 | +30 | 58–63 | Adaptado por proporción |
| 3 | 36 | 41–49 | +44 | 85–93 | Adaptado por proporción |
| 4 | 44 | 57–68 | +61 | 118–129 | Adaptado por proporción |
| 5 | 52 | 74–89 | +79 | 153–168 | Adaptado por proporción |
| 6 | 58 | 89–107 | +95 | 184–202 | Original WotLK |
| 7 | 66 | 116–140 | +95 | 211–235 | Original WotLK |
| 8 | 72 | 149–181 | +95 | 244–276 | Original WotLK |
| 9 | 78 | 180–220 | +95 | 275–315 | Original WotLK |
| — | 80 | 180–220 | +95 | 275–315 | Cierre, sin nuevo rango |

### Tabla completa por nivel, 20–80

Interpolación lineal entre anclas, por separado para mínimo, máximo y bonus. Redondeo al entero más cercano, mitades hacia arriba. Se conserva el último valor entre 78 y 80. Son valores base sin poder de ataque, críticos, talentos, resistencias ni bonificaciones de presencias. La implementación debe impedir que el escalado oculto del hechizo se aplique por segunda vez.

| Nivel | Base | Bonus con enfermedad | Base con enfermedad | Ira |
|---:|---|---:|---|---:|
| 20 | 16–19 | +17 | 33–36 | 20 |
| 21 | 18–21 | +19 | 37–40 | 20 |
| 22 | 19–23 | +20 | 39–43 | 20 |
| 23 | 21–24 | +22 | 43–46 | 20 |
| 24 | 22–26 | +24 | 46–50 | 20 |
| 25 | 24–28 | +25 | 49–53 | 20 |
| 26 | 25–30 | +27 | 52–57 | 20 |
| 27 | 27–31 | +28 | 55–59 | 20 |
| 28 | 28–33 | +30 | 58–63 | 20 |
| 29 | 30–35 | +32 | 62–67 | 20 |
| 30 | 31–37 | +34 | 65–71 | 20 |
| 31 | 33–39 | +35 | 68–74 | 20 |
| 32 | 35–41 | +37 | 72–78 | 20 |
| 33 | 36–43 | +39 | 75–82 | 20 |
| 34 | 38–45 | +41 | 79–86 | 20 |
| 35 | 39–47 | +42 | 81–89 | 20 |
| 36 | 41–49 | +44 | 85–93 | 20 |
| 37 | 43–51 | +46 | 89–97 | 20 |
| 38 | 45–54 | +48 | 93–102 | 20 |
| 39 | 47–56 | +50 | 97–106 | 20 |
| 40 | 49–59 | +53 | 102–112 | 20 |
| 41 | 51–61 | +55 | 106–116 | 20 |
| 42 | 53–63 | +57 | 110–120 | 20 |
| 43 | 55–66 | +59 | 114–125 | 20 |
| 44 | 57–68 | +61 | 118–129 | 20 |
| 45 | 59–71 | +63 | 122–134 | 20 |
| 46 | 61–73 | +66 | 127–139 | 20 |
| 47 | 63–76 | +68 | 131–144 | 20 |
| 48 | 66–79 | +70 | 136–149 | 20 |
| 49 | 68–81 | +72 | 140–153 | 20 |
| 50 | 70–84 | +75 | 145–159 | 20 |
| 51 | 72–86 | +77 | 149–163 | 20 |
| 52 | 74–89 | +79 | 153–168 | 20 |
| 53 | 77–92 | +82 | 159–174 | 20 |
| 54 | 79–95 | +84 | 163–179 | 20 |
| 55 | 82–98 | +87 | 169–185 | 20 |
| 56 | 84–101 | +90 | 174–191 | 20 |
| 57 | 87–104 | +92 | 179–196 | 20 |
| 58 | 89–107 | +95 | 184–202 | 20 |
| 59 | 92–111 | +95 | 187–206 | 20 |
| 60 | 96–115 | +95 | 191–210 | 20 |
| 61 | 99–119 | +95 | 194–214 | 20 |
| 62 | 103–124 | +95 | 198–219 | 20 |
| 63 | 106–128 | +95 | 201–223 | 20 |
| 64 | 109–132 | +95 | 204–227 | 20 |
| 65 | 113–136 | +95 | 208–231 | 20 |
| 66 | 116–140 | +95 | 211–235 | 20 |
| 67 | 122–147 | +95 | 217–242 | 20 |
| 68 | 127–154 | +95 | 222–249 | 20 |
| 69 | 133–161 | +95 | 228–256 | 20 |
| 70 | 138–167 | +95 | 233–262 | 20 |
| 71 | 144–174 | +95 | 239–269 | 20 |
| 72 | 149–181 | +95 | 244–276 | 20 |
| 73 | 154–188 | +95 | 249–283 | 20 |
| 74 | 159–194 | +95 | 254–289 | 20 |
| 75 | 165–201 | +95 | 260–296 | 20 |
| 76 | 170–207 | +95 | 265–302 | 20 |
| 77 | 175–214 | +95 | 270–309 | 20 |
| 78 | 180–220 | +95 | 275–315 | 20 |
| 79 | 180–220 | +95 | 275–315 | 20 |
| 80 | 180–220 | +95 | 275–315 | 20 |

### Fuentes verificadas

- Ventisca: https://www.wowhead.com/wotlk/es/spell=10/ventisca ; https://www.wowhead.com/wotlk/spell=6141/blizzard ; https://www.wowhead.com/wotlk/spell=8427/blizzard ; https://www.wowhead.com/wotlk/spell=10185/blizzard ; https://www.wowhead.com/wotlk/spell=10186/blizzard ; https://www.wowhead.com/wotlk/spell=10187/blizzard .
- Hervor: https://www.wowhead.com/wotlk/spell=48721/blood-boil ; https://www.wowhead.com/wotlk/spell=49939/blood-boil ; https://www.wowhead.com/wotlk/spell=49940/blood-boil ; https://www.wowhead.com/wotlk/spell=49941/blood-boil .
- Coeficientes y enfermedad: https://github.com/azerothcore/azerothcore-wotlk/blob/master/data/sql/base/db_world/spell_bonus_data.sql y https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/game/Entities/Unit/Unit.cpp . Consultado upstream, no la rama del usuario.

### Comprobaciones de implementación futuras

Comparar daño sin enfermedad, con una y con dos enfermedades, propias y ajenas; comprobar gasto único de 20 ira con varios objetivos; comprobar nivel mínimo 20; ausencia de efectos de runas/poder rúnico; coeficientes aplicados una sola vez; anclas originales sin cambios; GCD y radio; compatibilidad de familia/flags de los clones con el bonus de enfermedades de Unit.cpp. El script upstream de Hervor incluye una comprobación de clase DK: revisar su puente para Aventurero al implementar, sin heredar accidentalmente efectos de runas o generación de poder rúnico.

Verificación realizada aquí: anclas y las 61 filas calculadas, orden creciente y límites 20/80. No se ejecutó worldserver ni se modificó un repositorio.

## Estrangular — adaptación aprobada

Estado: valores aprobados por el usuario; registrados para implementar posteriormente. Sin cambios en una rama ni pruebas en cliente.

| Parámetro | Valor |
|---|---|
| Hechizo original de referencia | 47476 — Estrangular |
| Nivel inicial | 24 |
| Costo | 10 de ira |
| Alcance | Cuerpo a cuerpo, 5 yardas |
| Efecto principal | Silencio de 5 segundos, sin exigir que el objetivo esté lanzando |
| Contra objetivos no jugadores | Conservar la interrupción original de 3 segundos, respetando inmunidades |
| Reutilización | 60 segundos |
| Lanzamiento | Instantáneo |
| GCD | 1,5 segundos |
| Daño | Ninguno |
| Actitud requerida | Ninguna |
| Rangos | Uno, valores constantes de nivel 24 a 80 |

Cambiar costo de runas por ira sin generar poder rúnico. Conservar escuela de Sombras y disipación mágica nativas; cuerpo a cuerpo describe el alcance, no una conversión a daño físico. No añadir bloqueo de escuela de 8 segundos de Contrahechizo. La interrupción de criaturas no es un permiso para ignorar inmunidades ni lanzamientos no interrumpibles.

Referencia original consultada: https://www.wowhead.com/wotlk/spell=47476/strangulate . Referencia de comparación: https://www.wowhead.com/wotlk/spell=2139/counterspell .

Pruebas al implementar: nivel mínimo 24, costo 10 de ira, alcance de combate, silencio con y sin lanzamiento activo, interrupción contra criaturas, inmunidades, GCD 1,5 s y reutilización 60 s; ausencia de requisitos de actitud y de efectos de runas/poder rúnico.


# Escarcha: Presencia de escarcha y Toque helado aprobados

Presencia de escarcha y Toque helado aprobados por el usuario con los valores de esta sección. Pendientes de implementación y pruebas; las rarezas siguen sin definir.

## Presencia de escarcha

Nivel 1, sin rangos, mismos efectos hasta 80. Gratis, instantánea, CD de activación 1 s, sin GCD, duración indefinida. Conserva +8% aguante, +60% armadura de piezas de tela/cuero/malla/placas (no escudo), y −8% daño recibido. Amenaza aprobada explícita +45% (×1,45), sin duplicar modificadores ocultos del DK. No se afirma que ×1,45 sea el total efectivo original. Sin penalización de daño. Solo una presencia activa: Escarcha no coexiste con Sangre ni Profana. Mantener las reglas previamente acordadas respecto de actitudes; comprobar exclusiones nativas al implementar. Es una carta de tanque potente y no se afirma equivalencia con Actitud defensiva.

Fuente: https://www.wowhead.com/wotlk/spell=48263/frost-presence

## Toque helado

Nivel 1. Daño de Escarcha a 20 yardas, instantáneo, GCD 1,5 s, sin reutilización propia. Costo aprobado: 8% del maná base del Aventurero a su nivel, redondeado al entero más cercano, mínimo 1. No es maná máximo con intelecto/equipo. Sin requisito de presencia o actitud; sin runas ni generación de poder rúnico.

Daño directo: intervalo base de la tabla + 10% del poder de ataque. Se conserva PA, no se convierte a poder con hechizos solo por costar maná.

Fiebre de Escarcha propia: 15 s, un tick cada 3 s (5 ticks), sin tick inmediato añadido. Cada tick: 6,325% del PA, sin base fija añadida. Total teórico de cinco ticks: 31,625% PA antes de truncamientos. No aplicar nuevamente 1,15, ya incorporado en el coeficiente. Reduce velocidad de ataques cuerpo a cuerpo y a distancia en 14%; no reduce movimiento ni lanzamiento. Reaplicar refresca, no acumula. Enfermedad disipable y compatible con bonus de Sangriento/Hervor.

Amenaza especial APROBADA: ×7 para el impacto directo bajo nuestra Presencia de escarcha; luego ×1,45 general de la presencia (×10,15 antes de otros modificadores). No aplicar ×7 al DoT. Sin presencia: amenaza normal. Es un valor explícito de diseño, no una medición del repositorio del usuario. Validar multiplicadores y evitar duplicación al implementar.

Rarezas no definidas todavía para estas dos cartas; no confundir con el RARO aprobado para Golpe sangriento.

## Curva completa de Toque helado

Anclas custom aprobadas: nivel 1 = 8–9; nivel 8 = 16–17. Interpolar linealmente hasta el primer rango original de nivel 55. Anclas originales: 55 = 127–137; 61 = 144–156; 67 = 161–173; 73 = 187–203; 78 = 227–245. Mantener último valor hasta 80. Interpolar mínimo y máximo por separado; redondeo al entero más cercano con mitades hacia arriba. Las anclas bajas son decisiones nuevas de diseño, no datos Blizzard ni una curva derivada de Descarga de Escarcha.

Todas las filas cuestan 8% de maná base; son daño directo base, sin PA ni DoT.

| Nivel | Daño directo base |
|---:|---|
| 1 | 8–9 |
| 2 | 9–10 |
| 3 | 10–11 |
| 4 | 11–12 |
| 5 | 13–14 |
| 6 | 14–15 |
| 7 | 15–16 |
| 8 | 16–17 |
| 9 | 18–20 |
| 10 | 21–22 |
| 11 | 23–25 |
| 12 | 25–27 |
| 13 | 28–30 |
| 14 | 30–32 |
| 15 | 33–35 |
| 16 | 35–37 |
| 17 | 37–40 |
| 18 | 40–43 |
| 19 | 42–45 |
| 20 | 44–48 |
| 21 | 47–50 |
| 22 | 49–53 |
| 23 | 51–55 |
| 24 | 54–58 |
| 25 | 56–60 |
| 26 | 59–63 |
| 27 | 61–66 |
| 28 | 63–68 |
| 29 | 66–71 |
| 30 | 68–73 |
| 31 | 70–76 |
| 32 | 73–78 |
| 33 | 75–81 |
| 34 | 77–83 |
| 35 | 80–86 |
| 36 | 82–88 |
| 37 | 84–91 |
| 38 | 87–94 |
| 39 | 89–96 |
| 40 | 92–99 |
| 41 | 94–101 |
| 42 | 96–104 |
| 43 | 99–106 |
| 44 | 101–109 |
| 45 | 103–111 |
| 46 | 106–114 |
| 47 | 108–117 |
| 48 | 110–119 |
| 49 | 113–122 |
| 50 | 115–124 |
| 51 | 118–127 |
| 52 | 120–129 |
| 53 | 122–132 |
| 54 | 125–134 |
| 55 | 127–137 |
| 56 | 130–140 |
| 57 | 133–143 |
| 58 | 136–147 |
| 59 | 138–150 |
| 60 | 141–153 |
| 61 | 144–156 |
| 62 | 147–159 |
| 63 | 150–162 |
| 64 | 153–165 |
| 65 | 155–167 |
| 66 | 158–170 |
| 67 | 161–173 |
| 68 | 165–178 |
| 69 | 170–183 |
| 70 | 174–188 |
| 71 | 178–193 |
| 72 | 183–198 |
| 73 | 187–203 |
| 74 | 195–211 |
| 75 | 203–220 |
| 76 | 211–228 |
| 77 | 219–237 |
| 78 | 227–245 |
| 79 | 227–245 |
| 80 | 227–245 |

## Fuentes de Toque y enfermedad

- https://www.wowhead.com/wotlk/spell=45477/icy-touch
- https://www.wowhead.com/wotlk/spell=49896/icy-touch
- https://www.wowhead.com/wotlk/spell=49903/icy-touch
- https://www.wowhead.com/wotlk/spell=49904/icy-touch
- https://wowclassicdb.com/wotlk/spell/49909
- https://www.wowhead.com/wotlk/spell=55095/frost-fever
- Coeficientes upstream: https://github.com/azerothcore/azerothcore-wotlk/blob/master/data/sql/base/db_world/spell_bonus_data.sql (45477: 0,1 PA directo; 55095: 0,06325 PA por tick).

Verificación: tabla de 80 niveles y anclas originales comprobadas por cálculo. Pendiente de prueba: maná base real del Aventurero, ticks pequeños/redondeo, sinergias con enfermedades, generación de amenaza, buffs auxiliares y exclusión de presencias. No se modificó un repositorio ni se ejecutó worldserver.

## Helada mental y Cadenas de hielo — aprobadas

Valores de adaptación aprobados por el usuario, pendientes de implementación y pruebas. Ambas mantienen escuela de Escarcha, no requieren actitud ni presencia y no gastan runas ni generan poder rúnico. Costos sobre maná base del Aventurero al nivel correspondiente, no maná máximo; redondeo al entero más cercano, mínimo 1. Rarezas no asignadas.

| Parámetro | Helada mental | Cadenas de hielo |
|---|---|---|
| ID original | 47528 | 45524 |
| Nivel inicial aprobado | 12, referencia Patada | 8, referencia Seccionar |
| Costo aprobado | 3% maná base | 8% maná base |
| Alcance | Cuerpo a cuerpo, 5 yardas | 20 yardas |
| Lanzamiento | Instantáneo | Instantáneo |
| GCD | Sin GCD | 1,5 s |
| Reutilización | 10 s, original | 8 s, nueva para esta adaptación |
| Efecto | Interrumpe y bloquea la escuela interrumpida 4 s | Ralentización inicial 95%, recupera 10 puntos porcentuales de velocidad cada segundo, duración 10 s |
| Daño directo | Ninguno | Ninguno sin glifo |
| Enfermedad | Ninguna | Aplica/refresca Fiebre de Escarcha propia, 15 s |
| Rangos | Uno, nivel 12–80 sin cambios | Uno, nivel 8–80 sin cambios |

Helada mental no es silencio preventivo: si no interrumpe un lanzamiento válido no bloquea escuelas. Mantener reglas nativas de inmunidad y lanzamiento no interrumpible. Diferencia con Estrangular aprobado: interrupción frecuente sin GCD frente a silencio general 5 s con GCD y CD 60 s.

Cadenas no inmoviliza ni convierte automáticamente al objetivo en congelado. Ralentización en t=0/1/2/3/4/5/6/7/8/9/10 s: 95/85/75/65/55/45/35/25/15/5/0%. El efecto expira a los 10 s. Reaplicar reinicia ralentización y refresca la enfermedad, sin acumular copias del mismo lanzador. La ralentización es magia disipable y la enfermedad tiene su propia categoría; conservar inmunidades nativas. El CD de 8 s es deliberadamente nuevo: al sustituir runas por maná evita reaplicar 95% cada GCD.

Fiebre de Escarcha compartida con Toque helado: tick cada 3 s, cinco ticks en 15 s, 6,325% PA por tick y −14% velocidad de ataques cuerpo a cuerpo/a distancia. No crear una segunda enfermedad independiente al usar ambas cartas. No heredar el multiplicador especial de amenaza ×7 de Toque helado. La enfermedad sigue contando para Sangriento y Hervor.

Fuentes originales: https://www.wowhead.com/wotlk/spell=47528/mind-freeze ; https://www.wowhead.com/wotlk/spell=45524/chains-of-ice . Referencias de nivel: Patada nivel 12 https://www.wowhead.com/wotlk/spell=1766/kick y Seccionar nivel 8 https://www.wowhead.com/wotlk/spell=1715/hamstring . Costos de maná y CD de Cadenas son adaptaciones aprobadas, no valores Blizzard.

Verificar al implementar: umbrales de nivel, recursos, alcance/GCD/CD; bloqueo de una escuela frente a silencio; inmunidades; curva de ralentización; refresco y propiedad de enfermedad; ausencia de duplicación con Toque helado. Sin pruebas en servidor todavía.

## Asolar — diseño aprobado

El usuario propone maná y energía simultáneos. El original consume una runa de Escarcha y una Profana; inflige daño físico normalizado de arma y consume enfermedades propias para aumentar el daño. Es coherente adaptar sus dos recursos a maná + energía sin convertir su daño a mágico.

Mecánica aprobada: 8% del maná base + 30 de energía en el mismo lanzamiento; ambos obligatorios. Cuerpo a cuerpo (5 yardas), arma requerida, instantáneo, GCD 1,5 s, sin reutilización propia ni requisito de presencia/actitud. No consume puntos de combo, runas ni genera poder rúnico. Regla de combos aprobada: si el golpe impacta y el objetivo tenía al menos una enfermedad propia válida antes de consumirla, genera exactamente 1 punto de combo sobre ese objetivo. Sin enfermedad propia genera 0; varias enfermedades siguen dando solo 1. Fallo, esquiva o parada generan 0. Evaluar la condición antes de retirar las enfermedades y conceder el punto después de confirmar el impacto, una sola vez por lanzamiento exitoso.

Conservar 80% de daño de arma normalizado + adicional por nivel; multiplicar el total por (1 + 0,125 × enfermedades propias válidas). Sin enfermedades se puede usar igualmente. Si el golpe conecta, consumir las enfermedades propias según la mecánica nativa; no las de otros jugadores. Esto elimina su daño periódico restante y sus debuffs: no equivale a detonar el daño pendiente. No sumar bonificaciones por enfermedad de otros jugadores.

Anclas originales verificadas, adicionales efectivos después de 0,8: nivel 61 = 198,4 (248 × 0,8); 67 = 244 (305 × 0,8); 73 = 381,6 (477 × 0,8); 79 = 467,2 (584 × 0,8). Tooltips suelen mostrar 198/244/382/467. No volver a aplicar 0,8 al adicional efectivo. Fuentes: https://www.wowhead.com/wotlk/spell=49020/obliterate ; https://www.wowhead.com/wotlk/spell=51423/obliterate ; https://www.wowhead.com/wotlk/spell=51424/obliterate ; https://www.wowhead.com/wotlk/spell=51425/obliterate .

### Cierre de nivel, progresión y reglas de gasto

Mecánica y decisiones finales aprobadas por el usuario. Decisiones añadidas para completar el diseño: nivel inicial 20; rareza propuesta RARA; adicional inicial 40. Estos valores bajos son adaptación custom, no rangos originales. El 80% de arma se conserva en todos los niveles. El nivel 20 permite acceso después de Toque helado y Cadenas de hielo y deja que la combinación con enfermedades exista antes de recibir Asolar.

Una carta, niveles 20–80. Interpolar linealmente el adicional entre (20,40), (61,198.4), (67,244), (73,381.6), (79,467.2), (80,467.2); redondear a una décima, mitades hacia arriba. Conservar los cuatro valores nativos altos, sin aplicar otra vez el multiplicador 0,8 al adicional. El adicional inicial 40 es un punto de balance propuesto para probar, no una equivalencia demostrada con otro ataque.

Costo de maná: 8% del maná base del Aventurero al nivel actual, redondeo al entero más cercano, mitades hacia arriba, mínimo 1. Costo de energía fijo 30. Validar ambos recursos, objetivo, alcance y arma antes de cobrar; si la activación es inválida, no gastar ninguno. Una vez ejecutado el ataque, gastar ambos costos completos: para esta adaptación se define sin reembolso por fallo, esquiva, parada o inmunidad. No consumir enfermedades ni generar combo si no conecta. Bloqueo/absorción no se tratan como fallo: seguir el resultado de impacto del motor. Respetar máximo de combos; exceso perdido. No consumir combos existentes.

No se ha implementado soporte de costo dual. Mostrar ambos costos en tooltip y errores. Verificar: recursos insuficientes de uno u otro tipo, costo atómico, fallos e inmunidades, ausencia de reembolso; sin enfermedad = 0 combos; una propia = 1; dos propias = 1; solo ajenas = 0; consumo exclusivamente de enfermedades propias después de evaluar el bonus; límites de combos; cuatro anclas nativas y niveles bajos. Sin daño plano de amenaza adicional custom. Decisiones finales aprobadas: nivel 20, adicional inicial 40, rareza rara y ausencia de reembolso. Pendiente de implementación y pruebas en servidor.

### Asolar: tabla completa por nivel

Daño físico antes de armadura = (0,8 × daño normalizado de arma + adicional) × (1 + 0,125 × enfermedades propias válidas). La tabla muestra el adicional efectivo, no el daño total.

| Nivel | Adicional físico |
|---:|---:|
| 20 | 40,0 |
| 21 | 43,9 |
| 22 | 47,7 |
| 23 | 51,6 |
| 24 | 55,5 |
| 25 | 59,3 |
| 26 | 63,2 |
| 27 | 67,0 |
| 28 | 70,9 |
| 29 | 74,8 |
| 30 | 78,6 |
| 31 | 82,5 |
| 32 | 86,4 |
| 33 | 90,2 |
| 34 | 94,1 |
| 35 | 98,0 |
| 36 | 101,8 |
| 37 | 105,7 |
| 38 | 109,5 |
| 39 | 113,4 |
| 40 | 117,3 |
| 41 | 121,1 |
| 42 | 125,0 |
| 43 | 128,9 |
| 44 | 132,7 |
| 45 | 136,6 |
| 46 | 140,4 |
| 47 | 144,3 |
| 48 | 148,2 |
| 49 | 152,0 |
| 50 | 155,9 |
| 51 | 159,8 |
| 52 | 163,6 |
| 53 | 167,5 |
| 54 | 171,4 |
| 55 | 175,2 |
| 56 | 179,1 |
| 57 | 182,9 |
| 58 | 186,8 |
| 59 | 190,7 |
| 60 | 194,5 |
| 61 | 198,4 |
| 62 | 206,0 |
| 63 | 213,6 |
| 64 | 221,2 |
| 65 | 228,8 |
| 66 | 236,4 |
| 67 | 244,0 |
| 68 | 266,9 |
| 69 | 289,9 |
| 70 | 312,8 |
| 71 | 335,7 |
| 72 | 358,7 |
| 73 | 381,6 |
| 74 | 395,9 |
| 75 | 410,1 |
| 76 | 424,4 |
| 77 | 438,7 |
| 78 | 452,9 |
| 79 | 467,2 |
| 80 | 467,2 |

## Entereza ligada al hielo (48792) — aprobada

El usuario aprobó todos los valores de la propuesta siguiente. Las menciones a propuesta describen su origen; ya no está pendiente de aprobación. Sigue pendiente de implementación y pruebas.

Original WotLK: 20 poder rúnico; 12 s; CD 120 s; sin GCD; reducción de daño base 30% e inmunidad a aturdimientos. El script upstream añade floor(max(0, defensa total − 400) × 0,15) puntos porcentuales a la reducción. Defensa total es habilidad de defensa más contribución del índice de defensa, no índice bruto. No incluir el mínimo de 40% del glifo como si fuera base.

Propuesta: nivel 20; costo 5% del maná base del Aventurero al nivel correspondiente (redondeo al entero más cercano, mínimo 1); instantánea sobre uno mismo, sin GCD, CD 120 s, duración 12 s. Sin requisito de actitud, presencia, arma o escudo; sin runas ni poder rúnico. Un rango, nivel 20–80.

Conservar reducción base 30% e inmunidad a aturdimientos; no convertirla en inmunidad a miedo, silencio o cualquier control. Mantener restricciones nativas de lanzamiento: no prometer que elimina un aturdimiento ya activo ni agregar uso bajo control sin verificar flags del core/DBC al implementar.

Adaptación propuesta del bonus de defensa: sustituir 400 por 5 × nivel del personaje. Reducción en puntos porcentuales = 30 + floor(0,15 × max(0, D − 5 × nivel)), con D = habilidad efectiva de defensa más contribución del índice convertida a habilidad, truncada como en upstream. No usar directamente el índice bruto. No añade rangos: el bonus depende de defensa adicional, no sube por nivel por sí solo. A nivel 80 coincide con la referencia original de 400.

Ejemplos sin glifos/talentos: nivel 20 defensa 100 = 30%; nivel 20 defensa 120 = 33%; nivel 40 defensa 200 = 30%; nivel 80 defensa 400 = 30%; nivel 80 defensa 540 = 51%. Reducción de daño sujeta a las reglas del motor; no permitir daño recibido negativo en acumulaciones extremas.

Presencia de escarcha y Entereza pueden coexistir. Con reducciones de 8% y 30%, el daño restante es 0,92 × 0,70 = 0,644: reducción combinada 35,6%, antes de armadura y otros efectos. No sumar a 38% ni bloquear su combinación.

Fuentes: https://www.wowhead.com/wotlk/spell=48792/icebound-fortitude y https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/scripts/Spells/spell_dk.cpp (spell_dk_icebound_fortitude, consultado upstream). Nivel 20, costo de maná y referencia de defensa por nivel son adaptaciones propuestas, no valores Blizzard.

Pendiente de implementación y pruebas: costo, duración, CD/GCD; fórmula a niveles 20/40/80; coexistencia con defensivos; control de aturdimientos y restricciones de activación nativas; evitar duplicación del script original. Rareza no definida. No aplicado al repositorio.

## Cuerno de invierno — aprobado

Nivel inicial 10. Gratis, instantáneo, GCD 1,5 s, reutilización 20 s, buff de 120 s. Otorga Fuerza y Agilidad al lanzador y a miembros de grupo/banda en 30 yardas al lanzar; no exige permanecer cerca después. Sin requisito de actitud o presencia. Reaplicar refresca; no acumula copias del mismo Cuerno.

Generación de recurso propuesta: recuperar inmediatamente 5% del maná base del Aventurero, solo al lanzador, una vez por lanzamiento aunque afecte a muchos aliados. Redondear al entero más cercano, mínimo 1; limitar al maná máximo y perder el exceso. Se puede usar con cero maná, maná lleno o buff ya activo, dentro o fuera de combate. Eliminar generación de poder rúnico original; no cobrar runas, maná, salud ni otro recurso. 5% cada 20 s equivale a 0,25% de maná base por segundo en promedio, gastando un GCD por uso. Es un valor custom para probar.

Original: genera 10 de poder rúnico; nivel 65 otorga +86 y nivel 75 +155 a ambas estadísticas. Fuente: https://www.wowhead.com/wotlk/spell=57330/horn-of-winter y https://www.wowhead.com/wotlk/spell=57623/horn-of-winter .

Para niveles bajos se toman las anclas de Tótem Fuerza de la Tierra, que otorga las mismas estadísticas. Cada valor se aplica completo a Fuerza y a Agilidad, no se reparte entre ambas.

| Nivel | Fuerza | Agilidad | Fuente |
|---:|---:|---:|---|
| 10 | +10 | +10 | Tótem, 8075 |
| 24 | +20 | +20 | Tótem, 8160 |
| 38 | +36 | +36 | Tótem, 8161 |
| 52 | +61 | +61 | Tótem, 10442 |
| 60 | +77 | +77 | Tótem, 25361 |
| 65 | +86 | +86 | Cuerno original, 57330 |
| 75 | +155 | +155 | Cuerno original, 57623 |
| 80 | +155 | +155 | Cierre, sin nuevo rango |

Fuentes de anclas bajas: https://www.wowhead.com/wotlk/spell=8075/strength-of-earth-totem ; https://www.wowhead.com/wotlk/spell=8160/strength-of-earth-totem ; https://www.wowhead.com/wotlk/fr/spell=8161/totem-de-force-de-la-terre ; https://www.wowhead.com/wotlk/fr/spell=10442/totem-de-force-de-la-terre ; https://www.wowhead.com/wotlk/spell=25361/strength-of-earth-totem .

Una carta con interpolación lineal entre anclas; redondeo al entero más cercano, mitades hacia arriba. Mantener +155 de 75 a 80. Rareza no definida. No cambiar reglas de otras habilidades en esta tarea. Propuesta aprobada por el usuario, incluidos nivel inicial, recuperación de maná y progresión. Pendiente de implementación y pruebas; no probado en servidor.

### Cuerno: tabla completa por nivel

| Nivel | Fuerza | Agilidad |
|---:|---:|---:|
| 10 | +10 | +10 |
| 11 | +11 | +11 |
| 12 | +11 | +11 |
| 13 | +12 | +12 |
| 14 | +13 | +13 |
| 15 | +14 | +14 |
| 16 | +14 | +14 |
| 17 | +15 | +15 |
| 18 | +16 | +16 |
| 19 | +16 | +16 |
| 20 | +17 | +17 |
| 21 | +18 | +18 |
| 22 | +19 | +19 |
| 23 | +19 | +19 |
| 24 | +20 | +20 |
| 25 | +21 | +21 |
| 26 | +22 | +22 |
| 27 | +23 | +23 |
| 28 | +25 | +25 |
| 29 | +26 | +26 |
| 30 | +27 | +27 |
| 31 | +28 | +28 |
| 32 | +29 | +29 |
| 33 | +30 | +30 |
| 34 | +31 | +31 |
| 35 | +33 | +33 |
| 36 | +34 | +34 |
| 37 | +35 | +35 |
| 38 | +36 | +36 |
| 39 | +38 | +38 |
| 40 | +40 | +40 |
| 41 | +41 | +41 |
| 42 | +43 | +43 |
| 43 | +45 | +45 |
| 44 | +47 | +47 |
| 45 | +49 | +49 |
| 46 | +50 | +50 |
| 47 | +52 | +52 |
| 48 | +54 | +54 |
| 49 | +56 | +56 |
| 50 | +57 | +57 |
| 51 | +59 | +59 |
| 52 | +61 | +61 |
| 53 | +63 | +63 |
| 54 | +65 | +65 |
| 55 | +67 | +67 |
| 56 | +69 | +69 |
| 57 | +71 | +71 |
| 58 | +73 | +73 |
| 59 | +75 | +75 |
| 60 | +77 | +77 |
| 61 | +79 | +79 |
| 62 | +81 | +81 |
| 63 | +82 | +82 |
| 64 | +84 | +84 |
| 65 | +86 | +86 |
| 66 | +93 | +93 |
| 67 | +100 | +100 |
| 68 | +107 | +107 |
| 69 | +114 | +114 |
| 70 | +121 | +121 |
| 71 | +127 | +127 |
| 72 | +134 | +134 |
| 73 | +141 | +141 |
| 74 | +148 | +148 |
| 75 | +155 | +155 |
| 76 | +155 | +155 |
| 77 | +155 | +155 |
| 78 | +155 | +155 |
| 79 | +155 | +155 |
| 80 | +155 | +155 |

## Atracción letal — aprobada

Intención del usuario: taunt que consume energía. Propuesta completa: nivel 1, rareza RARA, 30 de energía, instantánea, alcance 30 yardas, CD 35 segundos, sin GCD. Sin requisito de presencia, actitud ni arma. Una carta sin rangos, nivel 1–80. No genera ni consume combos; no consume maná/runas ni genera poder rúnico; no causa daño.

Conservar el tirón original hacia el lanzador y su provocación de 3 segundos. Conservar las reglas nativas de amenaza del efecto de provocación; no sustituirlo por daño o amenaza plana. Respetar inmunidades a desplazamiento y provocación por separado: no permitir arrastrar jefes inmunes; el taunt puede funcionar cuando solo el desplazamiento es inmune. En jugadores, la provocación no fuerza sus decisiones; el tirón queda sujeto a inmunidades. Sin reinicio de reutilización por inmunidad y sin reembolso de energía tras lanzamiento válido, como decisión custom. Objetivo/alcance/línea de visión/recursos inválidos impiden lanzar sin cobrar. Mantener comprobaciones nativas de trayectoria y movimiento; no atravesar geometría mediante teletransporte custom.

Costo, nivel y rareza son propuestas nuestras. Alcance 30, CD 35 y GCD 0 conservan datos originales. Fuente: https://www.wowhead.com/wotlk/spell=49576/death-grip ; efecto de provocación: https://www.wowhead.com/wotlk/spell=49575/death-grip . Propuesta aprobada por el usuario, incluidos nivel inicial, rareza, costo y reglas de gasto. Pendiente de implementación y pruebas; no aplicado al repositorio.

## Golpe de peste — aprobado

Intención del usuario: generar combo. Propuesta completa: nivel 1, rareza COMÚN, 40 de energía, instantáneo, alcance cuerpo a cuerpo 5 yardas, GCD 1,5 segundos, sin reutilización propia. Requiere arma en mano principal; sin presencia/actitud. No consume maná ni runas y no genera poder rúnico.

Impacto físico = 50% del daño normalizado de arma + adicional efectivo por nivel. No multiplicar de nuevo el adicional por 0,5. No aumentar el daño directo por enfermedades: ese bonus no pertenece a esta habilidad. Aplicar/refrescar Peste de sangre propia durante 15 segundos. No consumir enfermedades. Peste de sangre y Fiebre de Escarcha son dos enfermedades distintas y pueden coexistir.

Genera exactamente 1 punto de combo sobre el objetivo cuando conecta, aunque antes no hubiera enfermedades, aunque ya tuviera Peste de sangre y aunque sea inmune solo a la enfermedad. El combo depende del impacto del arma, no de aplicar la enfermedad. No generar combo por ticks, reacciones, golpes adicionales de mano secundaria o propagación. Fallo/esquiva/parada/inmunidad al golpe = 0 combos, sin aplicar enfermedad por ese golpe. Bloqueo/absorción no equivalen a fallo: usar resultado de impacto del motor. Máximo y objetivo de combos según sistema existente; exceso perdido. No consume combos existentes. Así se distingue de Asolar, que exige enfermedad previa y la consume.

Peste de sangre (55078): daño de Sombras cada 3 segundos durante 15 segundos, 5 ticks; cada tick = 0,06325 × poder de ataque (0,055 × 1,15), antes de modificadores y redondeo nativo. Total base = 0,31625 × poder de ataque si completa los cinco ticks. Sin base plana añadida y sin escalado de poder con hechizos. Aplicar el factor 1,15 una sola vez. No genera combos, no elimina curaciones periódicas ni ralentiza. Refrescar la enfermedad propia sin apilar copias; conservar comportamiento nativo de temporizador de ticks. Esta fórmula escala con equipo/atributos, no necesita rangos propios. Fuentes: https://www.wowhead.com/wotlk/spell=55078/blood-plague ; https://www.wowhead.com/wotlk/spell=59879/blood-plague .

Gasto propuesto: validar arma, objetivo, alcance y energía antes de cobrar. Activación inválida no consume. Ataque ejecutado consume 40 de energía completos sin reembolso por fallo/esquiva/parada/inmunidad, regla custom coherente con Asolar; no presentar esta regla como reembolso nativo de pícaro. Sin amenaza plana extra custom.

Anclas originales efectivas: nivel 55 +62,5 (45462), 60 +75,5 (49917), 65 +89 (49918), 70 +108 (49919), 75 +157 (49920), 80 +189 (49921). Se conservan 50% de arma y todos estos adicionales. Anclas custom para niveles bajos: nivel 1 +4; nivel 8 +8. Son puntos de balance propuestos, no rangos Blizzard. Interpolación lineal entre todas las anclas, redondeo a una décima, mitades hacia arriba. Una carta con 80 filas de progresión.

Fuentes de rangos: https://www.wowhead.com/wotlk/spell=45462/plague-strike ; https://www.wowhead.com/wotlk/fr/spell=49917/frappe-de-peste ; https://www.wowhead.com/wotlk/fr/spell=49918/frappe-de-peste ; https://www.wowhead.com/wotlk/fr/spell=49919/frappe-de-peste ; https://www.wowhead.com/wotlk/spell=49920/plague-strike ; https://www.wowhead.com/wotlk/spell=49921/plague-strike .

Propuesta aprobada por el usuario, incluidos nivel inicial, rareza, costo, combo, enfermedad, progresión y ausencia de reembolso. Pendiente de implementación y pruebas de balance. Verificar costos, reglas de fallo, combo único, enfermedad propia, convivencia con Fiebre, consumo por Asolar, seis anclas nativas y primeros niveles. No implementado.

### Golpe de peste: tabla completa por nivel

El adicional se suma al 50% de arma; la enfermedad tiene la fórmula independiente anterior.

| Nivel | Adicional físico |
|---:|---:|
| 1 | 4,0 |
| 2 | 4,6 |
| 3 | 5,1 |
| 4 | 5,7 |
| 5 | 6,3 |
| 6 | 6,9 |
| 7 | 7,4 |
| 8 | 8,0 |
| 9 | 9,2 |
| 10 | 10,3 |
| 11 | 11,5 |
| 12 | 12,6 |
| 13 | 13,8 |
| 14 | 15,0 |
| 15 | 16,1 |
| 16 | 17,3 |
| 17 | 18,4 |
| 18 | 19,6 |
| 19 | 20,8 |
| 20 | 21,9 |
| 21 | 23,1 |
| 22 | 24,2 |
| 23 | 25,4 |
| 24 | 26,6 |
| 25 | 27,7 |
| 26 | 28,9 |
| 27 | 30,0 |
| 28 | 31,2 |
| 29 | 32,4 |
| 30 | 33,5 |
| 31 | 34,7 |
| 32 | 35,8 |
| 33 | 37,0 |
| 34 | 38,1 |
| 35 | 39,3 |
| 36 | 40,5 |
| 37 | 41,6 |
| 38 | 42,8 |
| 39 | 43,9 |
| 40 | 45,1 |
| 41 | 46,3 |
| 42 | 47,4 |
| 43 | 48,6 |
| 44 | 49,7 |
| 45 | 50,9 |
| 46 | 52,1 |
| 47 | 53,2 |
| 48 | 54,4 |
| 49 | 55,5 |
| 50 | 56,7 |
| 51 | 57,9 |
| 52 | 59,0 |
| 53 | 60,2 |
| 54 | 61,3 |
| 55 | 62,5 |
| 56 | 65,1 |
| 57 | 67,7 |
| 58 | 70,3 |
| 59 | 72,9 |
| 60 | 75,5 |
| 61 | 78,2 |
| 62 | 80,9 |
| 63 | 83,6 |
| 64 | 86,3 |
| 65 | 89,0 |
| 66 | 92,8 |
| 67 | 96,6 |
| 68 | 100,4 |
| 69 | 104,2 |
| 70 | 108,0 |
| 71 | 117,8 |
| 72 | 127,6 |
| 73 | 137,4 |
| 74 | 147,2 |
| 75 | 157,0 |
| 76 | 163,4 |
| 77 | 169,8 |
| 78 | 176,2 |
| 79 | 182,6 |
| 80 | 189,0 |

## Golpe letal — mecánica aprobada; tabla de niveles pendiente

Remate con energía y puntos de combo. Coste propuesto en la conversación y mantenido en el diseño: 35 de energía; requiere al menos 1 punto de combo sobre el objetivo y consume los puntos del remate, de 1 a 5. No exige enfermedades para poder usarse. No genera combos.

Regla expresamente aclarada y aprobada por el usuario: sea E el daño de referencia de Eviscerar al mismo nivel y con los mismos puntos de combo, antes de mitigación del enemigo. Golpe letal inflige daño físico base 0,50 × E y sana al lanzador 0,25 × E, además de su curación típica de 5% de la vida máxima del lanzador por enfermedad propia válida sobre el objetivo. Las enfermedades no se consumen. Sin enfermedades conserva toda la curación básica. No calcular la sanación como 25% del daño de Golpe letal ni como 25% del daño efectivo tras armadura. No interpretar 25% como porcentaje de vida máxima.

Ejemplo aprobado: E = 1000 implica 500 de daño físico antes de mitigación y 250 de curación básica; con una enfermedad propia se suma 5% de vida máxima y con Peste de sangre y Fiebre de Escarcha propias se suma 10%. Más combos aumentan E y por tanto ambas partes; la curación porcentual por enfermedades no se multiplica por combos.

Fuente de curación original por enfermedades: https://www.wowhead.com/wotlk/spell=49998/death-strike . El diseño de remate y los porcentajes de Eviscerar son personalizados.

No dar la habilidad por completamente cerrada: falta concretar la referencia numérica de Eviscerar y escribir la tabla completa por nivel y por 1–5 combos; fijar nivel inicial, rareza, GCD/alcance/reutilización, tratamiento del rango aleatorio y críticos en E, modificadores de sanación y reglas de fallo/reembolso/consumo de combos. No inventar una tabla de Eviscerar del proyecto ni asumir que coincide con una versión no inspeccionada. Pendiente de implementación y pruebas en servidor.

## Levantar muerto — versión provisional aceptada para pruebas

El usuario expresó reservas sobre esta adaptación, pero aceptó probarla tal como fue propuesta. No registrar como balance definitivo ni como probada.

Nivel inicial 10; rareza RARA; costo 50 de energía; instantáneo; GCD 1,5 segundos; duración del necrófago 60 segundos; reutilización 180 segundos contados desde la invocación. Sin cadáver ni Polvo de cadáver, sin requisito de presencia. No consume ni genera combos. Un único rango, necrófago del nivel del invocador. No añadir bonificaciones custom a daño o resistencia: conservar escalado nativo del necrófago y verificar funcionamiento en niveles bajos al implementar.

Invocar un necrófago temporal que combate automáticamente, no una mascota permanente controlable. Reservar la conversión a mascota permanente para un talento posterior; no otorgar Maestro de los necrófagos con esta carta. Máximo un necrófago de esta habilidad. La propuesta aceptada permite coexistir al guardián temporal con otra mascota; requiere verificar y, si hace falta, implementar esa convivencia sin reemplazar la mascota existente.

Los costos, nivel inicial, rareza, retirada de requisitos materiales, inicio del CD al invocar y coexistencia son decisiones de esta adaptación, no afirmaciones de comportamiento nativo. Referencias: https://www.wowhead.com/wotlk/spell=46584/raise-dead ; https://www.wowhead.com/wotlk/spell=52143/master-of-ghouls .

Pendiente de implementación y pruebas, sin cambios aplicados al repositorio. Evaluar especialmente: utilidad ofensiva frente al gasto de 50 energía, duración de 60 s y CD de 180 s; supervivencia y daño en niveles bajos; comportamiento automático; coexistencia con otra mascota; límite de una invocación; ausencia de requisito de cadáver/componente. No cerrar el balance hasta revisar la experiencia del usuario en juego. Reglas de errores de invocación, reembolso y transiciones de mascota requieren especificación/verificación al implementar; no afirmar que ya están resueltas.

### Nota alternativa de Levantar muerto — idea, NO sustituye la versión provisional

El usuario plantea únicamente como anotación: si el Aventurero mata a un enemigo y le quedan puntos de combo propios sobre ese enemigo que no gastó, se levanta el necrófago. Convertiría combos sobrantes al matar en una invocación automática. No es una modificación aprobada de la versión activa ni una orden de implementación. Conservar intacta la versión provisional anterior.

Viabilidad técnica comprobada en código upstream de AzerothCore: Unit expone GetComboPoints(who), GetComboTarget() y GetComboTargetGUID(). Unit.cpp limpia los combos asociados al objetivo al morir mediante ClearComboPointHolders(). Es viable desarrollar la mecánica del lado servidor, capturando los puntos asociados a esa víctima antes de su limpieza y confirmando muerte y autoría. Verificar orden real del remate/consumo de combos: un remate que gasta los puntos no debe interpretarse como combos sobrantes solo porque el callback de daño preceda al descuento. No se ha comprobado ni modificado la rama del proyecto.

Referencias inspeccionadas: https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/game/Entities/Unit/Unit.h ; https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/game/Entities/Unit/Unit.cpp .

Si se retoma la idea, definir duración, límite simultáneo, enfriamiento, atribución de bajas (mascota/grupo), enemigos válidos y si la cantidad de combos cambia alguna propiedad. No asignar valores nuevos por esta anotación.

## Muerte y descomposición — aprobada

Nivel inicial 20, rareza RARA, costo 60 de energía por lanzamiento, sin costos por tick ni por enemigo. Instantáneo, GCD 1,5 s, reutilización 30 s desde lanzamiento, área fija seleccionada en el suelo hasta 30 yardas, radio 10 yardas, duración 10 s, pulsos cada 1 s. No canalizada: permite moverse y usar otras habilidades. No requiere arma, actitud, presencia, enfermedades ni combos. No genera ni consume combos, runas o poder rúnico. No aplica ni consume enfermedades y no recibe bonus custom por ellas.

Daño de Sombras por pulso y enemigo = base por nivel + 0,04805 × poder de ataque, antes de modificadores/redondeo nativo. El coeficiente es el observado en upstream de AzerothCore para el disparador 52212 en spell_bonus_data.sql, no una atribución genérica a todos los servidores. Coeficiente de poder con hechizos 0. No agregarlo de nuevo en el aura y en el disparador: una sola aplicación. Mantener mitigación de áreas y modificadores nativos; no incluir glifos ni sets como bonus base.

Conservar amenaza elevada nativa, sin requisito de Presencia de escarcha; con esa presencia se combina con su modificador general. No es una provocación: no fuerza al enemigo a atacar ni iguala por sí sola la amenaza del tanque. Verificar factor efectivo de amenaza en los datos de la rama al implementar; no dar un multiplicador numérico por comprobado. Daño solo sobre objetivos dentro de la zona; no sigue al lanzador ni deja DoT persistente al salir.

Anclas originales: 60 = 26 (43265), 67 = 34 (49936), 73 = 49 (49937), 80 = 62 (49938), por pulso. Para bajar de nivel se usa la proporción de daño base de Ventisca ya empleada en Hervor: valores de Ventisca 20=200, 28=352, 36=520, 44=720, 52=936 y 60=1192. Base propuesta de Muerte y descomposición = redondeo(26 × referencia de Ventisca /1192): 20=4, 28=8, 36=11, 44=16, 52=20. Esto es una curva custom por proporción, no igualdad de daño ni compensación por canalización. Interpolar entre todas las anclas y redondear al entero más cercano, mitades hacia arriba. Mantener coeficiente de AP en todos los niveles.

Conservar inicio de ticks al aplicar del original. No escribir un total como 10 × pulso sin verificar la interacción del tick inicial y el final de duración en el motor; la tabla expresa daño por pulso, no total. Validar rango, posición y energía antes de cobrar. Una vez creada la zona se gasta el costo entero aunque ningún enemigo permanezca dentro; sin reembolso por pulsos vacíos o inmunes. Evitar cobros y generación de combos en disparadores.

Fuentes de habilidad y rangos: https://www.wowhead.com/wotlk/spell=43265/death-and-decay ; https://www.wowhead.com/wotlk/spell=49936/death-and-decay ; https://www.wowhead.com/wotlk/spell=49937/death-and-decay ; https://www.wowhead.com/wotlk/spell=49938/death-and-decay . Coeficiente y ejecución: https://github.com/azerothcore/azerothcore-wotlk/blob/master/data/sql/base/db_world/spell_bonus_data.sql ; https://github.com/azerothcore/azerothcore-wotlk/blob/master/src/server/scripts/Spells/spell_dk.cpp .

Diseño aprobado por el usuario: nivel 20, rareza rara, 60 de energía y progresión completa 20–80, junto con las mecánicas descritas. Pendiente de implementación y pruebas: curva baja, gasto único, AP sin duplicación, pulsos efectivos, amenaza elevada, geometría, entradas/salidas del área, independencia de combos y enfermedades. No aplicado al repositorio.

### Muerte y descomposición: tabla completa por nivel

A cada valor se suma 4,805% del poder de ataque por pulso y objetivo.

| Nivel | Daño base de Sombras por pulso |
|---:|---:|
| 20 | 4 |
| 21 | 5 |
| 22 | 5 |
| 23 | 6 |
| 24 | 6 |
| 25 | 7 |
| 26 | 7 |
| 27 | 8 |
| 28 | 8 |
| 29 | 8 |
| 30 | 9 |
| 31 | 9 |
| 32 | 10 |
| 33 | 10 |
| 34 | 10 |
| 35 | 11 |
| 36 | 11 |
| 37 | 12 |
| 38 | 12 |
| 39 | 13 |
| 40 | 14 |
| 41 | 14 |
| 42 | 15 |
| 43 | 15 |
| 44 | 16 |
| 45 | 17 |
| 46 | 17 |
| 47 | 18 |
| 48 | 18 |
| 49 | 19 |
| 50 | 19 |
| 51 | 20 |
| 52 | 20 |
| 53 | 21 |
| 54 | 22 |
| 55 | 22 |
| 56 | 23 |
| 57 | 24 |
| 58 | 25 |
| 59 | 25 |
| 60 | 26 |
| 61 | 27 |
| 62 | 28 |
| 63 | 29 |
| 64 | 31 |
| 65 | 32 |
| 66 | 33 |
| 67 | 34 |
| 68 | 37 |
| 69 | 39 |
| 70 | 42 |
| 71 | 44 |
| 72 | 47 |
| 73 | 49 |
| 74 | 51 |
| 75 | 53 |
| 76 | 55 |
| 77 | 56 |
| 78 | 58 |
| 79 | 60 |
| 80 | 62 |

## Caparazón antimagia — remate defensivo aprobado

Última decisión explícita del usuario: capacidad total de absorción por 1–5 combos = 15%, 30%, 45%, 60%, 75% de la vida máxima del lanzador. Sustituye las propuestas anteriores de duración por combos, capacidad 10–50% y capacidad 12,5–62,5%. La duración es siempre 5 segundos. El porcentaje absorbido de cada daño mágico permanece fijo en 75%; no confundirlo con la capacidad acumulada.

Parámetros mantenidos de la propuesta: nivel inicial 20, rareza RARA, costo 25 de energía más todos los puntos de combo disponibles (1–5), reutilización 45 segundos, instantáneo sobre uno mismo y sin GCD. Requiere al menos un punto de combo propio sobre un enemigo, pero no estar a distancia cuerpo a cuerpo. Sin requisito de arma, presencia o enfermedades. No genera poder rúnico ni otro recurso. Un rango para niveles 20–80: escala con vida máxima y combos, no con rangos por nivel.

| Combos consumidos | Capacidad acumulada sobre vida máxima | Duración | Fracción absorbida de cada daño mágico |
|---:|---:|---:|---:|
| 1 | 15% | 5 s | 75% |
| 2 | 30% | 5 s | 75% |
| 3 | 45% | 5 s | 75% |
| 4 | 60% | 5 s | 75% |
| 5 | 75% | 5 s | 75% |

Absorción por evento = mínimo entre 75% del daño mágico elegible y capacidad restante, con mitigación y orden de absorciones del motor. Termina al agotarse el escudo o expirar los 5 segundos. Mantener prevención nativa de aplicación de efectos mágicos perjudiciales mientras esté activo; no limpia los ya presentes ni protege de daño físico. No convertirlo en inmunidad total al daño mágico.

Comparación: el original tiene capacidad de 50% de vida máxima. Con la última tabla, 4 combos ya la superan (60%) y 5 dan 75%, un 50% más de capacidad que el original. Ya no afirmar equivalencia exacta entre 4 combos y original. Fuente: https://www.wowhead.com/wotlk/spell=48707/anti-magic-shell .

Pendiente de implementación y pruebas: consumo correcto de energía y combos en beneficio propio, sin requisito melee; validación antes de gasto; cálculo de capacidad y su agotamiento; prevención de efectos; duración fija; ausencia de generación de recurso; coexistencia con defensivos; nivel 20–80. Verificar flags nativos de uso bajo control y reglas del motor ante cambios de vida máxima, sin atribuir capacidades no comprobadas. No aplicado al repositorio.

## Presencia profana — alcance de adaptación aprobado

Decisión del usuario: por ahora conservar las habilidades afectadas por defecto y revisar después el resto del repertorio del Aventurero. Mantener +15% de velocidad de ataque cuerpo a cuerpo, +15% de movimiento y reducción de GCD de 0,5 segundos solo para las habilidades cubiertas por la configuración nativa. No convertir la reducción en un modificador universal ni extenderla por tipo de recurso. No acorta tiempos de lanzamiento ni reutilizaciones propias.

Mantener exclusión entre Presencia de sangre, Presencia de escarcha y Presencia profana: solo una activa; activar otra reemplaza la anterior. No extender esta exclusión a actitudes ni a defensivos como Entereza o Caparazón. Esta regla sustituye expresamente cualquier propuesta anterior de combinar varias presencias.

Sin rangos, de acuerdo con la regla general de presencias. No asumir que una habilidad clonada conserva automáticamente la elegibilidad del original: al implementar verificar máscaras/familias y la lista nativa, sin ampliar su alcance a otras familias. Verificar GCD efectivo y mínimos del motor, y que las habilidades sin GCD sigan sin GCD. Ampliación al resto de habilidades aplazada por el usuario.

Fuente previamente consultada: https://www.wowhead.com/wotlk/mx/spell=48265/presencia-profana . Pendiente de implementación y pruebas. El alcance del modificador y la exclusión entre presencias quedan aprobados; no se han aplicado cambios al repositorio.

## Ejército de muertos — costo triple aprobado

Decisión explícita final del usuario: consumir simultáneamente 50% del máximo de MANÁ, 50% del máximo de IRA y 50% del máximo de ENERGÍA. Requiere disponer de los tres importes; si falta cualquiera no se puede lanzar. No usar maná base ni porcentaje de recursos actuales. Sustituye las propuestas anteriores de 100 de energía y 100% de los tres recursos.

| Recurso | Costo obligatorio |
|---|---|
| Maná | 50% del maná máximo |
| Ira | 50% de la ira máxima |
| Energía | 50% de la energía máxima |

Con máximos de ira y energía de 100, cuesta 50 de cada uno. Si los máximos cambian, recalcular sus mitades: no fijar 50 puntos como costo universal. Para recursos enteros, redondear cada mitad hacia arriba a fin de no permitir lanzar por debajo del 50% requerido. Validar los tres importes y demás condiciones antes de cobrar; cobro atómico, sin gasto parcial, invocaciones ni inicio de reutilización si falla la validación. Cobrar una sola vez al comenzar la canalización, no por pulso ni por necrófago. Mostrar los tres costos y el recurso insuficiente en tooltip/errores.

Resto de la propuesta presentada, sin cambios solicitados: nivel 40, rareza ÉPICA, canalización de 4 segundos, GCD base 1,5 segundos sujeto a la elegibilidad nativa de Presencia profana, invocación progresiva de 8 necrófagos al completar, duración 40 segundos por necrófago, reutilización 10 minutos. Sin cadáveres, componentes, enfermedades ni combos. Un rango; invocaciones del nivel del Aventurero, con escalado nativo sin bonus custom de daño/resistencia.

Conservar reducción de daño durante la canalización equivalente a esquiva más parada según cálculo nativo, no una reducción plana permanente. Convivencia propuesta con el necrófago de Levantar muerto y otra mascota. Conservar provocaciones de los necrófagos respetando inmunidades y reglas nativas: pueden desordenar el combate. Si la canalización se interrumpe tras iniciarse, permanecen los ya invocados y no se reembolsan recursos ni reutilización.

Fuentes consultadas al proponer: https://www.wowhead.com/wotlk/spell=42650/army-of-the-dead ; https://www.wowhead.com/wotlk/spell=42651/army-of-the-dead . Costos y adaptación a nivel 40 son custom. Pendiente de implementación y pruebas; no aplicado al repositorio. Verificar costo triple atómico, máximos modificados, redondeo, interrupción, invocaciones parciales, ocho invocaciones completas, duración individual, coexistencia y provocaciones. No confundir aprobación del costo con pruebas realizadas.
