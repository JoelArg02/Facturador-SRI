import imaplib
import smtplib
import os
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from django.conf import settings


LOG_FILE = os.path.join(os.path.dirname(__file__), 'email_sender.log')


def _log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message)
    except Exception:
        pass


class EmailSender:
    
    def __init__(self):
        self.smtp_host = settings.EMAIL_HOST
        self.smtp_port = getattr(settings, 'EMAIL_PORT', 587)
        self.email_user = settings.EMAIL_HOST_USER
        self.email_password = settings.EMAIL_HOST_PASSWORD
        self.use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        _log(f"EmailSender inicializado - Host: {self.smtp_host}, Port: {self.smtp_port}, SSL: {self.use_ssl}, TLS: {self.use_tls}")
        
    def send_email(self, message: MIMEMultipart, recipients: list = None):
        try:
            if 'Date' not in message:
                message['Date'] = formatdate(localtime=True)
            
            if recipients is None:
                to_header = message.get('To', '')
                if isinstance(to_header, str):
                    recipients = [to_header] if to_header else []
                else:
                    recipients = to_header if isinstance(to_header, list) else [to_header]
            
            if isinstance(recipients, str):
                recipients = [recipients]
            
            subject = message.get('Subject', 'Sin asunto')
            _log(f"Enviando correo a {recipients} - Asunto: {subject}")
            
            server = None
            try:
                if self.use_ssl or self.smtp_port == 465:
                    _log(f"Conectando con SMTP_SSL a {self.smtp_host}:465")
                    server = smtplib.SMTP_SSL(self.smtp_host, 465)
                else:
                    _log(f"Conectando con SMTP a {self.smtp_host}:{self.smtp_port}")
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                    if self.use_tls:
                        _log("Iniciando STARTTLS")
                        server.starttls()
                
                _log(f"Autenticando como {self.email_user}")
                server.login(self.email_user, self.email_password)
                
                _log("Enviando mensaje SMTP")
                server.sendmail(self.email_user, recipients, message.as_string())
                _log(f"✓ Correo enviado exitosamente a {recipients}")
            finally:
                if server:
                    server.quit()
                    _log("Conexión SMTP cerrada")
            
            self._save_to_sent_folder(message)
            
            return True
            
        except Exception as e:
            _log(f"✗ ERROR al enviar correo: {str(e)}")
            raise
    
    def _save_to_sent_folder(self, message: MIMEMultipart):
        try:
            imap_host = self.smtp_host.replace('smtp', 'imap').replace('mail', 'imap')
            _log(f"Intentando guardar en bandeja de salida - IMAP Host: {imap_host}")
            
            _log("Conectando a IMAP SSL")
            imap = imaplib.IMAP4_SSL(imap_host)
            
            _log(f"Autenticando IMAP como {self.email_user}")
            imap.login(self.email_user, self.email_password)
            
            sent_folder_names = [
                'Sent',
                'INBOX.Sent',
                '[Gmail]/Sent Mail',
                'Sent Items',
                'Enviados',
                'Sent Messages'
            ]
            
            _log("Listando carpetas disponibles")
            _, folders = imap.list()
            available_folders = []
            for folder in folders:
                parts = folder.decode().split(' "/" ')
                if len(parts) > 1:
                    available_folders.append(parts[1].strip('"'))
                else:
                    parts = folder.decode().split('"')
                    if len(parts) >= 3:
                        available_folders.append(parts[-2])
            _log(f"Carpetas encontradas: {', '.join(available_folders)}")
            
            sent_folder = None
            for folder_name in sent_folder_names:
                if folder_name in available_folders:
                    sent_folder = folder_name
                    break
            
            if not sent_folder:
                for folder in available_folders:
                    if 'Sent' in folder or 'Enviados' in folder or 'sent' in folder.lower():
                        sent_folder = folder
                        break
            
            if not sent_folder:
                try:
                    _log("Creando carpeta 'Sent'")
                    imap.create('Sent')
                    sent_folder = 'Sent'
                except:
                    _log("No se pudo crear carpeta, usando INBOX")
                    sent_folder = 'INBOX'
            
            _log(f"Guardando mensaje en carpeta: {sent_folder}")
            imap.append(
                sent_folder,
                '\\Seen',
                imaplib.Time2Internaldate(time.time()),
                message.as_bytes()
            )
            
            imap.logout()
            _log(f"✓ Mensaje guardado exitosamente en {sent_folder}")
            
        except Exception as e:
            _log(f"⚠ Advertencia: No se pudo guardar en bandeja de salida: {str(e)}")


def send_email_with_sent_copy(message: MIMEMultipart, recipients: list = None):
    sender = EmailSender()
    return sender.send_email(message, recipients)
