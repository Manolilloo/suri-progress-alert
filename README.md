# Avisos de progreso de SURI

Este repositorio consulta PortWatch VI cada 10 minutos desde GitHub Actions y envía avisos push a ntfy. No necesita que tu ordenador esté encendido.

## Formato de la notificación

Una sola línea:

`61,0 % ⚡ 3 FPS | hyphennn`

- Porcentaje total actual de SURI, con la puntuación oficial de PortWatch.
- FPS que PortWatch publica actualmente para SURI. Se actualiza tanto si sube como si baja.
- Líder de la carrera pública de PortWatch. Los proyectos privados no tienen puesto en la clasificación oficial.
- Al tocar la notificación se abre la ficha de SURI.

No se cambia el icono de ntfy ni se envía una segunda imagen.

## Cuándo avisa

- Cuando la puntuación de SURI aumenta, aunque sea 0,1 puntos.
- Cuando cambian los FPS publicados para SURI, tanto al subir como al bajar.
- Cuando cambia el líder de la clasificación pública.

Una bajada aislada del porcentaje actualiza la referencia, pero no genera una alerta por sí sola.

## Configuración

1. La aplicación ntfy de Google Play debe estar suscrita al tema.
2. El repositorio necesita un secreto de Actions llamado `NTFY_TOPIC` con el tema de ntfy.
3. En **Actions → Probar notificación móvil** se puede enviar un simulacro con los valores reales que haya publicado PortWatch.

## Fuente y límites

El monitor lee `https://portwatch-vi.xyz/data/tracker.json` y replica el cálculo de `assets/js/scoring.js`. La clasificación pública se calcula igual que PortWatch: proyectos con código público, sin proyectos retirados, puntuación descendente y estrellas como desempate.

GitHub solicita una ejecución cada 10 minutos. Puede haber retrasos por carga de GitHub. PortWatch publica sus datos con menos frecuencia, por lo que consultar cada 10 minutos no adelanta su publicación.

El FPS mostrado es el valor que PortWatch tenga publicado en ese momento, no un pico de FPS medido por el monitor entre actualizaciones.
