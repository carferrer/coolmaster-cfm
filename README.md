# CoolMasterNet CFM

Integración personalizada para **Home Assistant 2026.9.2 o posterior**. Conserva
la demanda VRV y los seis botones de bloqueo de la versión CFM 1.0.5.
La versión 1.1.0 se basa en la integración oficial de HA 2026.9.2, con la
biblioteca de protocolo actualizada desde `pycoolmasternet-async` v0.2.6.

## Actualizar desde 1.0.5

1. Guarda una copia de tu carpeta actual `config/custom_components/coolmaster`.
2. Sustituye esa carpeta por `custom_components/coolmaster` de esta versión,
   incluyendo `translations` y `manifest.json`.
3. Reinicia Home Assistant.
4. Comprueba demanda, filtro, climatización y los botones con una unidad.

No borres ni vuelvas a crear la integración: se mantienen el dominio `coolmaster`,
la versión de configuración 1, los identificadores de dispositivos y los
`unique_id` originales, incluidas las claves `lock_on`, `unlock_on`, `lock_temp`,
`unlock_temp`, `lock_mode` y `unlock_mode`. Los nombres personalizados permanecen
en el registro de entidades existente.

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
- Prevención de entradas duplicadas por host y opción de activación para modelos serie.
- Tres intentos de lectura, con esperas de 2 y 4 segundos y sin espera tras el último fallo.
- Demanda mediante la propiedad pública; estado desconocido si el formato no la incluye.
- Siete botones implementados con descripciones; cada acción publica la lectura de su
  unidad, sin una consulta adicional de todo el puente.
- Unidades ausentes pasan a no disponibles y pueden eliminarse del registro.
- Traducciones independientes en español e inglés, sin claves JSON duplicadas.

Los botones envían órdenes; no representan ni verifican el estado actual del bloqueo.
Se mantiene ese comportamiento hasta disponer de una lectura confirmada del equipo.

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
