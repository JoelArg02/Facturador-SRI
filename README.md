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

Ejecutamos las migraciones para crear nuestra base de datos

```bash
python manage.py makemigrations
python manage.py migrate
```

Creamos los datos iniciales para iniciar nuestro proyecto

```bash
python manage.py start_installation
python manage.py insert_test_data (Opcional)
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

