# Biblioteca de protocolo incluida

Base: [OnFreund/pycoolmasternet-async, v0.2.6](https://github.com/OnFreund/pycoolmasternet-async/tree/v0.2.6).
Licencia MIT original conservada en `LICENSE`.

Extensiones CFM originales: [carferrer/pycoolmasternet-async-cfm, 82ba99c](https://github.com/carferrer/pycoolmasternet-async-cfm/tree/82ba99caa51c3468ce319f92529a14ebfb59f4cb).

Adaptaciones locales:

- Seis métodos de bloqueo originales, con implementación común y una lectura de la unidad.
- Consulta `lock <UID>` y análisis de los bloqueos de encendido, modo y consigna;
  si la respuesta no los indica, el estado permanece desconocido.
- Tiempo máximo para abrir la conexión, vaciado de escritura y errores claros ante EOF.
- Lecturas vacías como ausencia de unidades; validación de información y temperaturas.
- Coma decimal también en la consigna y conservación de identificadores largos.
- Saludos serie compatibles con Python 3.12 y posteriores.

Los archivos Python son la copia revisada de la propuesta local `0.2.6.post1`
de la biblioteca CFM. Esta propuesta no se ha publicado en PyPI ni en GitHub.
Se incluye aquí para que la integración sea instalable y no dependa de una rama
externa mutable. Al actualizar esta copia, ejecutar todas las pruebas de
`tests/test_protocol.py` y las de integración.
