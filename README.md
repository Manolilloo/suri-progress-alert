# Avisos de progreso de SURI

Este repositorio consulta el porcentaje del proyecto **SURI** en PortWatch VI cada 10 minutos desde GitHub Actions. No necesita que tu ordenador esté encendido. Envía una notificación push a ntfy únicamente cuando el porcentaje sube.

## Activación

1. Instala ntfy en el móvil desde https://ntfy.sh/ y suscríbete al tema indicado en esta conversación.
2. En este repositorio abre **Settings → Secrets and variables → Actions → New repository secret**.
3. Crea un secreto llamado `NTFY_TOPIC` y pega como valor el tema al que te has suscrito en ntfy. No lo pongas en archivos públicos.
4. Abre la pestaña **Actions**, entra en **Vigilar progreso de SURI** y pulsa **Run workflow** para hacer una primera prueba.
5. Comprueba que la ejecución termina correctamente. Las siguientes comprobaciones se ejecutan automáticamente cada 10 minutos.

## Qué vigila

Lee `https://portwatch-vi.xyz/data/tracker.json`, busca únicamente el proyecto cuyo id es `suri` y reproduce el cálculo de puntuación que usa PortWatch. El valor inicial guardado es **61,0 %**. Solo se avisa cuando el valor aumenta; los descensos actualizan la referencia sin mandar avisos.

La puntuación de PortWatch se publica con una precisión de una décima. Por tanto, el monitor detecta cualquier subida que el tracker llegue a reflejar (por ejemplo, de 61,0 a 61,1).

## Frecuencia y limitaciones

- GitHub Actions solicita una comprobación cada 10 minutos.
- GitHub puede retrasar los trabajos programados en horas de mucha carga; no es una garantía de ejecución exacta al minuto.
- PortWatch publica los datos del tracker aproximadamente cada 3 horas. Consultar cada 10 minutos no adelanta la publicación del dato.
- El repositorio es público para utilizar los runners estándar gratuitos de GitHub Actions.
- GitHub puede desactivar los workflows programados de repositorios públicos tras 60 días sin actividad. Si pasa, basta con volver a habilitarlo en Actions.

## Seguridad

El tema ntfy es público en el sentido de que quien conozca su nombre puede publicar o suscribirse. Por eso usamos un nombre aleatorio largo y lo guardamos como secreto de GitHub. No publiques ese nombre en el repositorio.
