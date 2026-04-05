# File Processing Challenge - Arquitectura y Ejecución

Este repositorio contiene la logica para procesar archivos CSV con millones de registros de forma asíncrona, almacenar los datos en PostgreSQL y procesarlos diariamente utilizando flujos automatizados con n8n.

## Tecnologías Utilizadas

- **FastAPI:** Para la creación de la API y recepción de archivos.
- **Python (Generadores):** Para el procesamiento eficiente de datos a través de *streaming*.
- **PostgreSQL:** Sistema de gestión de bases de datos relacional.
- **Azure Queue Storage / Blob Storage (Azurite):** Para simular colas y almacenamiento en la nube de forma local.
- **Docker & Docker Compose:** Para orquestar toda la infraestructura de la aplicación.
- **n8n:** Herramienta Node-based de automatización de flujos.
- **SQLAlchemy:** ORM (aunque para inserción masiva usamos sentencias SQL puras).

## Arquitectura y Decisiones Técnicas 

El sistema se diseñó bajo una arquitectura en **Capas**. Cuando un archivo se sube por el endpoint `/upload`, el motor web (FastAPI) delega el almacenamiento en Blob Storage y emite un mensaje a una Cola. Un componente independiente (Worker) escucha esta cola, descarga el archivo procesándolo por partes para no saturar la memoria RAM, e inserta a PostgreSQL sin bloquear los *requests* entrantes a la API.

### 1. Estrategia de Descarga por *Streaming*

**La Decisión:** Implementar generadores en Python (`yield`) iterando sobre los *chunks* HTTP del cliente de Azure (`blob_client.download_blob().chunks()`). Esto no lo habia usado pero es una buena herramienta.

**Por qué:** El proposito era procesar millones de registros, entonces si se intentan cargar los archivos totalmente la RAM se va a saturar, aparte es un problema de N+1 muy común. La forma que escogi para solucionarlo fue leer por flujos (Streams), el memory footprint es mínimo y estable, sin importar si el archivo pesa 10 MB o 5 GB.

### 2. Estrategia de Inserción Masiva (PostgreSQL `COPY`)

**La Decisión:** Utilizo SQLAlchemy como ORM para consultas a la DB pero para este caso en especifico de insercion masiva opté por usar `cursor.copy_expert("COPY ... FROM STDIN WITH CSV")` creando chunks de 10,000 registros.
**Por qué:** Realizar millones de `INSERT` sentencias u ORM `add_all()` sature y colapsa la DB con  validación tipo-objeto y la constante comunicación de red. El comando `COPY` es una herramienta optimizada en PostgreSQL para inserciones masivas. consideré usarla priorizando mas la eficiencia en este caso.

**Desventajas de `COPY`:**
1. **Validación limitada:** Si una de las 10,000 filas de un lote tiene un tipo de dato inválido (ej. string en vez de integer), la transacción de todo el paquete falla. La falta de validación silenciosa requiere limpiezas rigurosas previas.
2. **Manejo de Errores Rígido:** Es más difícil identificar con exactitud la línea exacta que está corrupta en comparación a inserciones individuales.
3. **Poco agnóstico:** limitaria el proyecto a usar la sintaxis nativa de PostgreSQL.

---

## Ejecución con Docker Compose

Para levantar todos los componentes uso **Docker Compose**. Contiene la Base de Datos, el API, el Worker en Background, n8n y un emulador local de Azure.

### Dependencia Clave: Azurite
Para no requerir cuentas conectadas a Azure Cloud durante las pruebas ni arriesgar cobros o limitantes en cuentas gratuitas, el entorno Docker despliega [Azurite](https://github.com/Azure/Azurite). Este proyecto oficial de Microsoft emula en local las APIs de Blob Storage, Queue Storage y Table Storage sobre HTTP en los puertos 10000 y 10001, inyectándolo transparente al SDK de Azure.

### Pasos para Arrancar la Aplicación

1. Clona el repositorio.
2. Construye y levanta la infraestructura en tu terminal:
   ```bash
   docker-compose up --build -d
   ```
3. Verifica que los servicios estén activos:
   * API FastAPI (Swagger Docs): `http://localhost:8000/docs`
   * n8n Panel General: `http://localhost:5678`

---

## Cómo importar el Workflow de N8N 

El contenedor de N8N ya estará levantado usando tu BD como data-store, ahora configuraremos el flujo automatizado:

1. Ingresa a `http://localhost:5678` y configura la cuenta de primer ingreso (puede ser cualquier correo durante el local testing).
2. En la interfaz principal de n8n, clica en **Workflows**, luego en **Add Workflow**.
3. Accede al menú de opciones arriba a la derecha (*tres puntos*) y selecciona **Import from File**.
4. Sube el archivo `n8n_daily_sales_workflow.json` que encuentras en la raíz del proyecto.
5. Autoriza las credenciales de conexión de la Base de Datos con PostgreSQL (en `/docker-compose.yml` puedes ver las credenciales) y activa el *toggle* principal de tu flujo (si aplica). Para testear, utiliza el botón "Test Workflow". 

*(Nota: el flujo usa un disparador periódico "Schedule Trigger", consulta las celdas terminadas de los jobs y aplica `INSERT ... ON CONFLICT (date) DO UPDATE` para popular la tabla `sales_daily_summary`).*

---

### Pasos para ejecutar corectamente el flujo de procesamiento

1. Luego de instalarlo y correr con docker toda la infra, se debe subir un archivo a traves del endpoint `/upload`. en la carpeta `/files_test` dejo un archivo con 2M de registros o si desean en la carpeta `/app/scripts` hay una logica para generar el archivo del tamaño que consideren.

2. Automaticamente se subira el archivo a contenedor local de azure, se envia el mensaje a traves de la cola y el worker pasará a insertar los registros y retornara un mensaje en la consola al terminar.

3. Con la configuracion de las crendenciales de la DB, el registro inicial en N8N(local) y la importacion de workflow `/workflows/N8N_sales_daily_summary.json`. solo se debe ejecutar el flujo completo para luego verificar la insercion o actualizacion de los registros en la tabla `sales_daily_summary`.

## Ejecución de Pruebas Unitarias (Tests) 

El proyecto incluye tests unitarios para garantizar el éxito de funcionalidades claves evitando integraciones pesadas mediante partición del código.

*(Nota: Opcionalmente puedes correr los tests localmente creando un Virtual Enviroment o correrlos dentro del mismo contenedor Docker).*

Ejecutar dentro del contenedor:
```bash
docker exec -it logyca_api pytest
```

*(Si instalas el servidor Python local)*:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -v app/tests/
```