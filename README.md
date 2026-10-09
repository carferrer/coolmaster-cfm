# CoolMasterNet CFM

Integración personalizada para **Home Assistant 2026.9.2 o posterior**. Conserva
la demanda VRV y permite consultar y controlar los bloqueos del mando local.
La versión 1.2.0 se basa en la integración oficial de HA 2026.9.2, con la
biblioteca de protocolo actualizada desde `pycoolmasternet-async` v0.2.6.

## Actualizar desde 1.0.5

1. Guarda una copia de tu carpeta actual `config/custom_components/coolmaster`.
2. Sustituye esa carpeta por `custom_components/coolmaster` de esta versión,
   incluyendo `translations` y `manifest.json`.
3. Reinicia Home Assistant.
4. Comprueba demanda, filtro, climatización y los interruptores de bloqueo con una unidad.

No borres ni vuelvas a crear la integración: se mantienen el dominio `coolmaster`,
la versión de configuración 1 y los identificadores de dispositivos. El botón
de filtro mantiene su `unique_id`. Los seis botones de bloqueo se reemplazan por
tres entidades `switch` (`lock_on`, `lock_temp`, `lock_mode`). Los botones antiguos
pueden quedar como entradas huérfanas en el registro de entidades de Home
Assistant; tras reiniciar, se pueden eliminar allí y actualizar las
automatizaciones que los usaban.

## Máquinas Daikin con dos velocidades

Después de instalar, abre **Ajustes → Dispositivos y servicios → CoolMasterNet →
Reconfigurar**. En **Velocidades de ventilador disponibles**, deja marcadas solo
**Baja (`low`)** y **Alta (`high`)** y guarda. Home Assistant mostrará únicamente
esas dos opciones en todas las unidades de este puente. No hay que crear otra
integración ni cambiar los identificadores de las entidades.

Una entrada ya configurada sigue mostrando `low`, `med`, `high` y `auto` hasta que
se reconfigure. Así se conservan las automatizaciones existentes. La selección
se aplica a todo el puente; usa `low` y `high` cuando todas sus unidades los
soportan, como en esta instalación.

Se conserva **`med`** como velocidad pública del ventilador para no romper
automatizaciones existentes. Esta es una diferencia deliberada respecto a la
normalización a `medium` del componente oficial.

La biblioteca revisada está incluida en `custom_components/coolmaster/_vendor`,
separada del módulo oficial y con su licencia MIT. No requiere instalar paquetes
externos ni publicar primero una nueva versión del fork. El manifiesto tiene
`requirements: []`; todo el protocolo incluido usa la biblioteca estándar de Python.
Su procedencia y las adaptaciones están documentadas en `_vendor/README.md`.

## Cambios

- Reconfiguración de conexión y modos desde la interfaz; conserva el puerto existente.
- Selección de velocidades del ventilador desde la reconfiguración.
- Prevención de entradas duplicadas por host y opción de activación para modelos serie.
- Tres intentos de lectura, con esperas de 2 y 4 segundos y sin espera tras el último fallo.
- Demanda mediante la propiedad pública; estado desconocido si el formato no la incluye.
- Un botón de filtro y tres interruptores de bloqueo por unidad. Cada interruptor
  consulta `lock <UID>` en el puente y muestra su respuesta real, también cuando
  el bloqueo se cambia fuera de Home Assistant. Tras una orden, vuelve a leer
  esa unidad sin consultar el puente completo.
- Unidades ausentes pasan a no disponibles y pueden eliminarse del registro.
- Traducciones independientes en español e inglés, sin claves JSON duplicadas.

La consulta de bloqueos añade una petición por unidad en cada actualización.
Si un puente no admite `lock <UID>` o no informa de un bloqueo concreto, su
interruptor aparece como **no disponible** en lugar de asumir que está desactivado.
El protocolo está documentado en el [manual de CoolAutomation](https://support.coolautomation.com/hc/en-us/articles/7068465434397-CoolMaster-PRM-Programmers-Reference-Manual).

## Pruebas de desarrollo

Con Python 3.14:

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q
ruff check .
ruff format --check .
```

Las pruebas usan las clases reales de Home Assistant 2026.9.2 con comunicación
simulada. La biblioteca tiene pruebas de protocolo con un servidor TCP local.
La validación con un puente físico y una instalación completa de HA queda pendiente.

## Procedencia

Base de integración: [Home Assistant Core 2026.9.2](https://github.com/home-assistant/core/tree/2026.9.2/homeassistant/components/coolmaster), Apache-2.0.
Biblioteca: [pycoolmasternet-async v0.2.6](https://github.com/OnFreund/pycoolmasternet-async/tree/v0.2.6), MIT.
Extensiones CFM: demanda y bloqueos de [carferrer](https://github.com/carferrer).
