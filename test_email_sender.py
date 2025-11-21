"""
Script de prueba para verificar el envío de correos con copia en bandeja de salida.
Ejecutar con: python manage.py shell < test_email_sender.py
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.pos.utilities.email_sender import send_email_with_sent_copy
from django.conf import settings

# Crear mensaje de prueba
message = MIMEMultipart('alternative')
message['Subject'] = 'Correo de Prueba - OptimusPos'
message['From'] = settings.EMAIL_HOST_USER
message['To'] = settings.EMAIL_HOST_USER  # Enviar a uno mismo para prueba

text_content = """
Hola,

Este es un correo de prueba del sistema OptimusPos.
Si recibes este correo, significa que el sistema de envío está funcionando correctamente.

Además, este correo debería aparecer en tu bandeja de salida.

Saludos,
Sistema OptimusPos
"""

html_content = """
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #2563eb;">Correo de Prueba - OptimusPos</h2>
    <p>Hola,</p>
    <p>Este es un correo de prueba del sistema OptimusPos.</p>
    <p>Si recibes este correo, significa que el sistema de envío está funcionando correctamente.</p>
    <p><strong>Además, este correo debería aparecer en tu bandeja de salida.</strong></p>
    <br>
    <p>Saludos,<br>Sistema OptimusPos</p>
</body>
</html>
"""

message.attach(MIMEText(text_content, 'plain'))
message.attach(MIMEText(html_content, 'html'))

# Enviar correo
try:
    result = send_email_with_sent_copy(message)
    if result:
        print("✓ Correo enviado exitosamente")
        print("✓ Verifica tu bandeja de entrada y de salida")
    else:
        print("✗ Error al enviar el correo")
except Exception as e:
    print(f"✗ Error: {e}")
