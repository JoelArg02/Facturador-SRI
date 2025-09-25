# Refactor SaaS (Multi-tenant) – Progreso

Este documento registra los pasos iterativos para transformar el sistema (originalmente mono-empresa) en una plataforma SaaS multi-tenant con planes y cuotas.

## Objetivos generales
1. Separar datos por compañía (tenant) asegurando aislamiento lógico.
2. Definir planes con límites (facturas, clientes, productos).
3. Asociar compañías a suscripciones activas y validar cuotas en creación de recursos.
4. Mantener compatibilidad temporal con la estructura previa mientras migramos.

## Iteración 1 (actual)
Estado: COMPLETADA

Cambios introducidos:
- Nueva app `core.subscription` con modelos:
	- `Plan`: define límites y precio.
	- `Subscription`: vincula `Company` con un `Plan` y controla vigencia.
- Campo `owner` agregado a `Company` para identificar el usuario propietario (opcional durante migración).
- Servicios de cuota (`core.subscription.services.ensure_quota`) con excepción `QuotaExceeded`.
- Método helper en `Company`:
	- `active_subscription()`
	- `can_create(kind)` para validar antes de persistir.
- Comando de gestión `seed_plans` para crear planes base (Starter, Pro, Enterprise).
- Registro en admin de Plan y Subscription.
- Actualización de `INSTALLED_APPS` agregando `core.subscription`.

Notas:
- Aún no se ha añadido la clave foránea `company` a todos los modelos operativos (Product, Provider, etc.). Eso se hará gradualmente para minimizar riesgo.
- La validación de cuotas para `customer` y `product` funcionará plenamente una vez que esos modelos estén asociados a `Company` (próxima iteración).

## Próxima Iteración (planificada)
1. (Hecho en Iteración 2) Añadir `company` a `Provider`, `Category`, `Product`, `Customer`, `Receipt`, `ExpenseType`, `Expense`, `Promotion`, `PromotionDetail`, etc.
2. (Hecho en Iteración 2) Comando de backfill para asignar compañía a registros existentes.
3. (Pendiente) Ajustar consultas y vistas para filtrar por compañía activa del usuario.
4. (Pendiente) Selector de compañía (si un usuario tiene varias).
5. (Pendiente) Ampliar `ensure_quota` usando conteos filtrados por compañía en todos los modelos.

## Iteración 2
Estado: EN PROGRESO

Cambios:
- FK `company` agregada a modelos principales (provider, category, product, purchase, purchase detail, cuentas por pagar/cobrar, customer, receipt, expense*, promotion* y detalles).
- Comando `backfill_company_fk` para asignar la compañía existente a los registros previos.
- Middleware `ActiveCompanyMiddleware` para inyectar `request.company`.
- Mixin `CompanyQuerysetMixin` para filtrar automáticamente por compañía y setearla al crear.
- Vistas de productos adaptadas a multi-tenant.
- Vistas adaptadas adicionales: receipt, receipt_error, account_payable, account_receivable, credit_note (admin y customer, impresión) todas usando `CompanyQuerysetMixin`.

Pasos para aplicar:
```bash
source venv/bin/activate
python manage.py makemigrations core.pos
python manage.py migrate
python manage.py backfill_company_fk
```

Dry run (vista previa):
```bash
python manage.py backfill_company_fk --dry-run
```

Siguientes pasos dentro de Iteración 2 (pendientes):
1. Actualizar vistas restantes: invoice, purchase, expense, expense_type, promotion, customer, provider, category, stock/otros módulos auxiliares.
2. Integrar chequeo de cuotas en creaciones (customer, product, invoice) antes de guardar.
3. Añadir tests unitarios mínimos para cuotas y aislamiento (acceso cruzado prohibido).
4. Implementar selector de compañía (si un usuario posee varias) y almacenar en sesión.


## Cómo probar (local)
Activar entorno virtual (asumiendo venv en raíz) y ejecutar la instalación integral (ya no necesitas correr makemigrations/migrate manualmente):

```bash
source venv/bin/activate
python manage.py start_installation
```

Crear una suscripción para la compañía existente en shell Django:

```bash
python manage.py shell
```
Ya no es estrictamente necesario (se crea automáticamente si no existe). Solo si quieres cambiar de plan:
```python
from core.pos.models import Company
from core.subscription.models import Plan, Subscription
c = Company.objects.first()
plan = Plan.objects.get(name='Pro')
Subscription.objects.create(company=c, plan=plan)
```

Validar helper de cuotas:

```python
c.can_create('invoice')  # (True, None) si está dentro del límite
```

## Consideraciones futuras
- Middleware para establecer `request.company` derivado de usuario / selección.
- Auditoría por tenant.
- Hard delete vs soft delete (posible agregado de campo `is_deleted`).
- Índices compuestos por `company` para optimizar queries.

---
Este archivo se irá ampliando en cada iteración.

# PASOS DE INSTALACIÓN

### CURSOS DE RESPALDO

| Nombre del Video | Enlace                                                                                    |
| ---------------- |-------------------------------------------------------------------------------------------|
| Curso de Python con Django de 0 a Máster | [Ver aquí](https://youtube.com/playlist?list=PLxm9hnvxnn-j5ZDOgQS63UIBxQytPdCG7 "Enlace") |
| Curso de Deploy de un Proyecto Django en un VPS Ubuntu | [Ver aquí](https://youtube.com/playlist?list=PLxm9hnvxnn-hFNSoNrWM0LalFnSv5oMas "Enlace")           |
| Curso de Python con Django Avanzado I | [Ver aquí](https://www.youtube.com/playlist?list=PLxm9hnvxnn-gvB0h0sEWjAf74ge4tkTOO "Enlace")       |
| Curso de Python con Django Avanzado II | [Ver aquí](https://www.youtube.com/playlist?list=PLxm9hnvxnn-jL7Fqr-GL2iSPfgJ99BhEC "Enlace")       |

### INSTALADORES

| Nombre        | Instalador                                                                                                                                                                                                                                           |
|:--------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| 
| Compilador    | [Python3](https://www.python.org/downloads/release/python-31011/ "Python3")                                                                                                                                                                                                                                |
| IDE           | [Visual Studio Code](https://code.visualstudio.com/ "Visual Studio Code"), [Sublime Text](https://www.sublimetext.com/ "Sublime Text"), [Pycharm](https://www.jetbrains.com/es-es/pycharm/download/#section=windows "Pycharm")                       |
| Base de datos | [Sqlite Studio](https://github.com/pawelsalawa/sqlitestudio/releases "Sqlite Studio"), [PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads "PostgreSQL"), [MySQL](https://www.apachefriends.org/es/index.html "MySQL") |

### INSTALACIÓN DEL PROYECTO

Clonamos el proyecto en nuestro directorio seleccionado

```bash
git clone URL
```

Creamos nuestro entorno virtual para poder instalar las librerías del proyecto

```bash
python3.10 -m venv venv o virtualenv venv -ppython3.10
source venv/bin/active
```

Instalamos Java en su computador, esto es importante para poder firmar los comprobantes con la firma electrónica

Para windows:

```bash
https://www.java.com/es/download/
```

Para linux:

```bash
https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-ubuntu-20-04-es
```

Instalamos el complemento para la librería WEASYPRINT

Si estas usando Windows debe descargar el complemento de [GTK3 installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases "GTK3 installer"). En algunas ocaciones se debe colocar en las variables de entorno como primera para que funcione y se debe reiniciar el computador.

Si estas usando Linux debes instalar las [librerias](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#linux "librerias") correspondientes a la distribución que tenga instalado en su computador.

Instalamos las librerías del proyecto

```bash
pip install -r deploy/txt/requirements.txt
```

Instalación (crea migraciones, migra y siembra todo en un solo paso):

```bash
python manage.py start_installation
```

Datos de prueba (Opcional):

```bash
python manage.py insert_test_data
```

Iniciamos el servidor del proyecto

```bash
python manage.py runserver 0:8000 
username: admin
password: hacker94
```

# Pasos para la creación del cron de envió de comprobantes electrónicos

Tener instalado cron en tu servidor de linux

```bash
sudo apt install cron
```

Crear una nueva tarea en tu cron

```bash
crontab -e
```

Crear la tarea de envio de correos en el cron, la palabra user hace referencia al usuario de tu server

```bash
*/1 * * * * /bin/bash -c 'source /home/jdavilav/invoice/venv/bin/activate && cd /home/jdavilav/invoice && python manage.py electronic_billing' >> /tmp/invoice.log 2>&1
```

Reiniciar el servicio del cron en el servidor

```bash
sudo /etc/init.d/cron restart
```

------------

# Gracias por adquirir mi producto ✅🙏

#### Esto me sirve mucho para seguir produciendo mi contenido 🤗​

### ¡Apóyame! para seguir haciéndolo siempre 😊👏

Paso la mayor parte de mi tiempo creando contenido y ayudando a futuros programadores sobre el desarrollo web con tecnología open source.

🤗💪¡Muchas Gracias!💪🤗

**Puedes apoyarme de la siguiente manera.**

**Suscribiéndote**
https://www.youtube.com/c/AlgoriSoft?sub_confirmation=1

**Siguiendo**
https://www.facebook.com/algorisoft

**Donando por PayPal**
williamjair94@hotmail.com

***AlgoriSoft te desea lo mejor en tu aprendizaje y crecimiento profesional como programador 🤓.***

