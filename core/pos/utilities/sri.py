import base64
import os.path
import random
import string
import subprocess
from datetime import datetime
from itertools import cycle
from pathlib import Path
from tempfile import NamedTemporaryFile

import requests
from django.core.files import File
from lxml import etree
from suds.client import Client

from config import settings
from core.pos.choices import VOUCHER_STAGE, INVOICE_STATUS


class SRI:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)

    def get_absolute_path(self, path):
        return str(Path(path).absolute())

    def compute_mod11(self, pass_key_48=''):
        if len(pass_key_48) > 48:
            return ''
        addition = 0
        factors = cycle((2, 3, 4, 5, 6, 7))
        for digit, factor in zip(reversed(pass_key_48), factors):
            addition += int(digit) * factor
        number = 11 - addition % 11
        if number == 11:
            number = 0
        elif number == 10:
            number = 1
        return str(number)

    def generate_number(self, amount=8):
        return ''.join(random.choices(list(string.digits), k=amount))

    def create_access_key(self, instance):
        password_48 = f"{datetime.now().strftime('%d%m%Y')}{instance.receipt.voucher_type}{instance.company.ruc}{instance.company.environment_type}{instance.receipt.establishment_code}{instance.receipt.issuing_point_code}{instance.receipt_number}{self.generate_number()}{instance.company.emission_type}"
        module11 = self.compute_mod11(pass_key_48=password_48)
        if len(module11):
            return f'{password_48}{module11}'
        return None

    def get_receipt_url(self, instance):
        if instance.company.environment_type == 2:
            return 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
        return 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'

    def get_authorization_url(self, instance):
        if instance.company.environment_type == 2:
            return 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
        return 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'

    def create_xml(self, instance):
        response = {'resp': False, 'stage': VOUCHER_STAGE[1][0]}
        try:
            xml, access_code = instance.create_xml_document()
            instance.access_code = access_code
            instance.save()
            response['resp'] = True
            response['xml'] = xml
        except Exception as e:
            response['error'] = str(e)
        finally:
            if 'error' in response:
                instance.create_receipt_error(errors=response)
        return response

    def firm_xml(self, instance, xml):
        response = {'resp': False, 'stage': VOUCHER_STAGE[1][0]}
        file_temp_name = ''
        try:
            with NamedTemporaryFile(suffix='.xml', delete=False) as file_temp:
                file_temp.write(xml.encode())
                file_temp.flush()
                file_temp_name = file_temp.name
                jar_path = self.get_absolute_path(os.path.join(os.path.dirname(self.base_dir), 'files/jar/sri.jar'))
                certificate_path = self.get_absolute_path(f'{settings.BASE_DIR}/{instance.company.get_electronic_signature()}')
                certificate_key = instance.company.electronic_signature_key
                xml_name = f'{instance.receipt_number}.xml'
                commands = ['java', '-jar', jar_path, certificate_path, certificate_key, file_temp.name, self.base_dir, xml_name]
                procedure = subprocess.run(args=commands, capture_output=True)
                if procedure.returncode == 0:
                    error = procedure.stdout.decode('utf-8')
                    if error.__contains__('Error'):
                        response['error'] = error
                    else:
                        generated_xml_path = os.path.join(self.base_dir, xml_name)
                        with open(generated_xml_path, 'rb') as file:
                            response['resp'] = True
                            response['xml'] = file.read().decode('utf-8')
                        if os.path.exists(generated_xml_path):
                            os.remove(generated_xml_path)
                else:
                    response['error'] = procedure.stderr.decode('utf-8')
        except Exception as e:
            response['error'] = str(e)
        finally:
            if os.path.exists(file_temp_name):
                os.remove(file_temp_name)
            if 'error' in response:
                instance.create_receipt_error(errors=response)
        return response

    def validate_xml(self, instance, xml):
        response = {'resp': False, 'stage': VOUCHER_STAGE[2][0]}
        try:
            document = xml.strip().encode('utf-8')
            base64_binary_xml = base64.b64encode(document).decode('utf-8')
            sri_client = Client(self.get_receipt_url(instance))
            result = sri_client.service.validarComprobante(base64_binary_xml)
            status = result.estado
            if status == 'DEVUELTA':
                receipt = result.comprobantes.comprobante[0]
                response['error'] = {'access_code': receipt.claveAcceso, 'errors': []}
                for count, value in enumerate(receipt.mensajes):
                    message = value[1][count]
                    values = dict()
                    for name in ['identificador', 'informacionAdicional', 'mensaje', 'tipo']:
                        if name in message:
                            values[name] = message[name]
                    response['error']['errors'].append(values)
            elif status == 'RECIBIDA':
                response['resp'] = True
                response['xml'] = xml
        except Exception as e:
            response['error'] = str(e)
        finally:
            if 'error' in response:
                instance.create_receipt_error(errors=response)
        return response

    def authorize_xml(self, instance):
        response = {'resp': False, 'stage': VOUCHER_STAGE[3][0]}
        try:
            sri_client = Client(self.get_authorization_url(instance))
            result = sri_client.service.autorizacionComprobante(instance.access_code)
            if len(result):
                receipt = result[2].autorizacion[0]
                if receipt.estado == 'NO AUTORIZADO':
                    response['error'] = {'access_code': instance.access_code, 'stage': receipt.estado, 'authorized_date': str(receipt.fechaAutorizacion), 'errors': []}
                    for count, value in enumerate(receipt.mensajes):
                        message = value[1][count]
                        values = dict()
                        for name in ['identificador', 'informacionAdicional', 'mensaje', 'tipo']:
                            if name in message:
                                values[name] = message[name]
                        response['error']['errors'].append(values)
                else:
                    xml_authorization = etree.Element('autorizacion')
                    etree.SubElement(xml_authorization, 'estado').text = receipt.estado
                    etree.SubElement(xml_authorization, 'numeroAutorizacion').text = receipt.numeroAutorizacion
                    etree.SubElement(xml_authorization, 'fechaAutorizacion', attrib={'class': "fechaAutorizacion"}).text = str(receipt.fechaAutorizacion.strftime("%d/%m/%Y %H:%M:%S"))
                    voucher_sri = etree.SubElement(xml_authorization, 'comprobante')
                    voucher_sri.text = etree.CDATA(receipt.comprobante)
                    xml_text = etree.tostring(xml_authorization, encoding="utf8", xml_declaration=True).decode('utf8').replace("'", '"')
                    with NamedTemporaryFile(delete=True) as file_temp:
                        xml_path = f'xml/{instance.receipt.get_name_file()}-{instance.receipt_number_full}.xml'
                        file_temp.write(xml_text.encode())
                        file_temp.flush()
                        instance.authorized_xml.save(name=xml_path, content=File(file_temp))
                        instance.authorized_date = receipt.fechaAutorizacion
                        # Generar y adjuntar PDF autorizado inmediatamente
                        try:
                            instance.create_authorized_pdf()
                        except Exception:
                            pass
                        instance.status = INVOICE_STATUS[1][0]
                        instance.save()
                        response['resp'] = True
        except Exception as e:
            response['error'] = str(e)
        finally:
            if 'error' in response:
                instance.create_receipt_error(errors=response)
        return response

    def send_receipt_by_email(self, instance):
        response = {'resp': False, 'stage': VOUCHER_STAGE[4][0]}
        try:
            instance.status = INVOICE_STATUS[2][0]
            customer = instance.get_client_from_model()
            response = instance.send_invoice_files_to_customer()
            if response['resp']:
                instance.save()
        except Exception as e:
            response['error'] = str(e)
            instance.create_receipt_error(errors=response)
        return response

    def search_ruc_in_sri(self, ruc):
        response = {'error': 'El número de ruc es inválido'}
        url = f'https://srienlinea.sri.gob.ec/movil-servicios/api/v1.0/estadoTributario/{ruc}'
        try:
            r = requests.get(url, timeout=10)
            print(r.status_code, r.text[:200])
            if r.status_code == requests.codes.ok:
                response = r.json()
            elif r.status_code == 503:
                response = {'error': 'El servicio del SRI no está disponible en este momento. Intente más tarde.'}
            else:
                try:
                    response['error'] = r.json().get('mensaje', 'Error inesperado en el servicio del SRI')
                except Exception:
                    response['error'] = f'Error del servicio SRI (HTTP {r.status_code})'
        except requests.exceptions.RequestException as e:
            response = {'error': f'No se pudo conectar con el SRI: {e}'}
        return response

