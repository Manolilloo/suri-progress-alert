# Avisos del progreso global de PortWatch

Este repositorio consulta el tracker completo de PortWatch cada 5 minutos desde GitHub Actions y envía avisos push al móvil mediante ntfy. No necesita que el ordenador esté encendido.

## Qué vigila

- El porcentaje más alto de todos los proyectos activos del tracker, que marca el líder global.
- El monitor incluye proyectos públicos, privados y forks nuevos en cuanto aparecen en `data/tracker.json`.
- Se ignoran únicamente los proyectos marcados como retirados (`nuked`), igual que hace PortWatch.
- Se envía una notificación cuando el máximo global sube, aunque sea solo 0,1 puntos porcentuales.

No se sigue un proyecto fijo como SURI, hyphennn, Belobug, DexNom u otro. El líder y su porcentaje se vuelven a calcular desde cero en cada comprobación.

## Formato de la notificación

Título: `Progreso GTAVI`

Mensaje, en una sola línea:

`78,7 % ⚡ 4 FPS | Doomsday`

El porcentaje, los FPS y el nombre pertenecen al líder global actual. Si un fork nuevo supera al líder anterior, aparecerá automáticamente en el siguiente aviso cuando el porcentaje máximo aumente.

Al tocar la notificación se abre PortWatch: https://portwatch-vi.xyz/

## Cuándo avisa

- Cuando el máximo global aumenta respecto a la comprobación anterior, incluidos incrementos de 0,1.
- No avisa por cambios de FPS ni por cambios de nombre si el porcentaje máximo no ha subido.
- Si el máximo baja, actualiza la referencia sin mandar aviso; si vuelve a subir en una comprobación posterior, vuelve a avisar.

## Configuración

1. La aplicación ntfy debe estar suscrita al tema correspondiente.
2. El repositorio necesita un secreto de Actions llamado `NTFY_TOPIC` con ese tema.
3. La acción `Vigilar progreso global de PortWatch` se ejecuta cada cinco minutos. 
4. `Probar notificación móvil` envía un simulacro con los datos del líder global actual.

## Fuente y funcionamiento

El monitor consulta `https://portwatch-vi.xyz/data/tracker.json` con cabeceras y parámetro anti-caché, y replica el cálculo de `assets/js/scoring.js`. La clasificación se calcula con todos los proyectos no retirados, ordenados por porcentaje y, en caso de empate, estrellas de GitHub.

Si PortWatch no entrega un JSON válido o no hay proyectos activos verificables, la ejecución falla sin inventar porcentajes ni enviar alertas.

GitHub Actions puede retrasar las ejecuciones programadas por carga del servicio. PortWatch también publica cambios por tandas, así que el aviso llega cuando el dato nuevo aparece en su tracker.
