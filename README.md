# Avisos de progreso de SURI

Este repositorio consulta los datos de PortWatch cada 5 minutos desde GitHub Actions y envía avisos al móvil mediante ntfy. No necesita que el ordenador esté encendido.

## Qué vigila

- El porcentaje se calcula exclusivamente para el proyecto cuyo `id` es `suri`.
- Se envía una notificación únicamente cuando ese porcentaje sube, aunque sea solo 0,1 puntos.
- El progreso general del tracker y el porcentaje del líder no activan alertas de SURI.

## Qué aparece en la notificación

Título: `Progreso GTAVI`

Mensaje, en una sola línea:

`61,0 % ⚡ 3 FPS | Doomsday`

El porcentaje y los FPS pertenecen a SURI. El nombre final corresponde al líder actual de la clasificación general de PortWatch. Se vuelve a calcular en cada revisión con todos los proyectos que no estén retirados, incluidos los proyectos privados y los que se incorporen nuevos. Se usa el nombre del proyecto y, si no está disponible, su id.

Un cambio de líder por sí solo no manda una notificación. Cuando SURI vuelva a subir, el aviso incluirá el líder que haya en ese momento, aunque haya cambiado varias veces desde el aviso anterior.

Al tocar la notificación se abre la ficha de SURI: https://portwatch-vi.xyz/#effort-suri

## Configuración

1. La aplicación ntfy debe estar suscrita al tema utilizado.
2. El repositorio necesita un secreto de Actions llamado `NTFY_TOPIC` con ese tema.
3. La acción `Vigilar progreso de SURI` comprueba los datos cada cinco minutos y también permite ejecuciones manuales desde GitHub Actions.

## Fuente y funcionamiento

El monitor consulta `https://portwatch-vi.xyz/data/tracker.json` sin usar caché y replica el cálculo de `assets/js/scoring.js`. Busca exactamente una entrada con `id: "suri"`; si no puede verificarla, falla sin inventar un porcentaje ni enviar una alerta.

GitHub Actions puede retrasar una ejecución programada por carga del servicio. PortWatch también publica los datos por tandas, así que una revisión no implica que el porcentaje haya cambiado.
