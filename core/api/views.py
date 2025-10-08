import json
from datetime import datetime
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from core.pos.utilities.sri import SRI


@method_decorator(csrf_exempt, name='dispatch')
class InvoiceAPIView(View):
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            company_data = data.get('company')
            if not company_data:
                return JsonResponse({'error': 'company es requerido'}, status=400)
            
            customer_data = data.get('customer')
            if not customer_data:
                return JsonResponse({'error': 'customer es requerido'}, status=400)
            
            products_data = data.get('products', [])
            if not products_data:
                return JsonResponse({'error': 'Debe enviar al menos un producto'}, status=400)
            
            receipt_data = data.get('receipt')
            if not receipt_data:
                return JsonResponse({'error': 'receipt es requerido'}, status=400)
            
            date_joined = data.get('date_joined', datetime.now().strftime('%Y-%m-%d'))
            payment_type = data.get('payment_type', 'contado')
            payment_method = data.get('payment_method', '01')
            create_electronic = data.get('create_electronic_invoice', True)
            additional_info = data.get('additional_info', [])
            
            subtotal_with_tax = 0.0
            subtotal_without_tax = 0.0
            total_discount = 0.0
            total_tax = 0.0
            
            tax_rate = float(company_data.get('tax_rate', 0.15))
            
            details = []
            for product_data in products_data:
                quantity = int(product_data.get('quantity', 1))
                price = float(product_data.get('price', 0))
                discount_percent = float(product_data.get('discount', 0)) / 100
                has_tax = product_data.get('has_tax', True)
                
                subtotal = price * quantity
                discount_amount = subtotal * discount_percent
                total_amount = subtotal - discount_amount
                
                if has_tax:
                    tax_amount = total_amount * tax_rate
                    subtotal_with_tax += total_amount
                    total_tax += tax_amount
                else:
                    tax_amount = 0
                    subtotal_without_tax += total_amount
                
                total_discount += discount_amount
                
                details.append({
                    'code': product_data.get('code'),
                    'name': product_data.get('name'),
                    'quantity': quantity,
                    'price': price,
                    'discount': discount_percent,
                    'total_discount': discount_amount,
                    'total_amount': total_amount,
                    'tax_amount': tax_amount,
                    'has_tax': has_tax
                })
            
            subtotal = subtotal_with_tax + subtotal_without_tax
            total_amount = subtotal + total_tax
            
            sri = SRI()
            
            receipt_number = receipt_data.get('receipt_number')
            receipt_number_full = f"{receipt_data.get('establishment_code')}-{receipt_data.get('issuing_point_code')}-{receipt_number}"
            
            password_48 = f"{datetime.now().strftime('%d%m%Y')}{receipt_data.get('voucher_type')}{company_data.get('ruc')}{company_data.get('environment_type')}{receipt_data.get('establishment_code')}{receipt_data.get('issuing_point_code')}{receipt_number}{sri.generate_number()}{company_data.get('emission_type')}"
            access_code = f"{password_48}{sri.compute_mod11(password_48)}"
            
            response_data = {
                'success': True,
                'receipt_number_full': receipt_number_full,
                'access_code': access_code,
                'subtotal': round(subtotal, 2),
                'subtotal_with_tax': round(subtotal_with_tax, 2),
                'subtotal_without_tax': round(subtotal_without_tax, 2),
                'total_discount': round(total_discount, 2),
                'total_tax': round(total_tax, 2),
                'total_amount': round(total_amount, 2),
                'details': details
            }
            
            if create_electronic:
                try:
                    signature_path = company_data.get('electronic_signature_path')
                    signature_key = company_data.get('electronic_signature_key')
                    
                    if not signature_path or not signature_key:
                        return JsonResponse({
                            'error': 'Para generar factura electrónica debe proporcionar electronic_signature_path y electronic_signature_key en los datos de company'
                        }, status=400)
                    
                    import os
                    if not os.path.exists(signature_path):
                        return JsonResponse({
                            'error': f'El archivo de firma electrónica no existe en la ruta: {signature_path}'
                        }, status=400)
                    
                    xml_response = self.generate_xml(
                        company_data, 
                        customer_data, 
                        receipt_data, 
                        details, 
                        response_data,
                        date_joined,
                        payment_type,
                        payment_method,
                        access_code,
                        tax_rate,
                        additional_info
                    )
                    
                    if xml_response.get('xml'):
                        response_data['xml'] = xml_response['xml']
                        
                        firm_response = self.firm_xml(
                            xml_response['xml'],
                            signature_path,
                            signature_key,
                            receipt_number
                        )
                        
                        if firm_response.get('xml_signed'):
                            response_data['xml_signed'] = firm_response['xml_signed']
                            
                            validate_response = self.validate_xml_with_sri(
                                firm_response['xml_signed'],
                                company_data.get('environment_type', 1)
                            )
                            
                            if validate_response.get('resp'):
                                response_data['sri_validation'] = {
                                    'status': 'RECIBIDA',
                                    'message': 'Comprobante recibido por el SRI'
                                }
                                
                                authorize_response = self.authorize_xml_with_sri(
                                    access_code,
                                    company_data.get('environment_type', 1)
                                )
                                
                                if authorize_response.get('resp'):
                                    response_data['sri_authorization'] = {
                                        'status': 'AUTORIZADO',
                                        'authorization_number': authorize_response.get('authorization_number'),
                                        'authorization_date': authorize_response.get('authorization_date'),
                                        'message': 'Comprobante autorizado por el SRI'
                                    }
                                    return JsonResponse(response_data, status=200)
                                else:
                                    response_data['sri_authorization'] = {
                                        'status': 'NO AUTORIZADO',
                                        'errors': authorize_response.get('errors', []),
                                        'message': 'Comprobante no autorizado por el SRI'
                                    }
                                    return JsonResponse(response_data, status=422)
                            else:
                                response_data['sri_validation'] = {
                                    'status': 'DEVUELTA',
                                    'errors': validate_response.get('errors', []),
                                    'message': 'Comprobante devuelto por el SRI'
                                }
                                return JsonResponse(response_data, status=422)
                        else:
                            return JsonResponse({
                                'error': 'Error al firmar XML',
                                'details': firm_response.get('error', 'Error desconocido al firmar'),
                                'receipt_number_full': response_data['receipt_number_full'],
                                'access_code': response_data['access_code']
                            }, status=500)
                    else:
                        return JsonResponse({
                            'error': 'Error al generar XML',
                            'details': xml_response.get('error', 'Error desconocido al generar XML')
                        }, status=500)
                        
                except Exception as e:
                    return JsonResponse({
                        'error': 'Error en el proceso de facturación electrónica',
                        'details': str(e)
                    }, status=500)
            
            return JsonResponse(response_data, status=201)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def generate_xml(self, company, customer, receipt, details, totals, date_joined, payment_type, payment_method, access_code, tax_rate, additional_info):
        try:
            from xml.etree import ElementTree
            
            root = ElementTree.Element('factura', id='comprobante', version='1.0.0')
            
            xml_tax_info = ElementTree.SubElement(root, 'infoTributaria')
            ElementTree.SubElement(xml_tax_info, 'ambiente').text = str(company.get('environment_type'))
            ElementTree.SubElement(xml_tax_info, 'tipoEmision').text = str(company.get('emission_type'))
            ElementTree.SubElement(xml_tax_info, 'razonSocial').text = company.get('company_name')
            ElementTree.SubElement(xml_tax_info, 'nombreComercial').text = company.get('commercial_name')
            ElementTree.SubElement(xml_tax_info, 'ruc').text = company.get('ruc')
            ElementTree.SubElement(xml_tax_info, 'claveAcceso').text = access_code
            ElementTree.SubElement(xml_tax_info, 'codDoc').text = receipt.get('voucher_type')
            ElementTree.SubElement(xml_tax_info, 'estab').text = receipt.get('establishment_code')
            ElementTree.SubElement(xml_tax_info, 'ptoEmi').text = receipt.get('issuing_point_code')
            ElementTree.SubElement(xml_tax_info, 'secuencial').text = receipt.get('receipt_number')
            ElementTree.SubElement(xml_tax_info, 'dirMatriz').text = company.get('main_address')
            
            regimen_rimpe = company.get('regimen_rimpe', '')
            if regimen_rimpe and regimen_rimpe != 'CONTRIBUYENTE RÉGIMEN GENERAL':
                ElementTree.SubElement(xml_tax_info, 'contribuyenteRimpe').text = regimen_rimpe
            
            if company.get('retention_agent') == 'SI':
                ElementTree.SubElement(xml_tax_info, 'agenteRetencion').text = '1'
            
            xml_info_invoice = ElementTree.SubElement(root, 'infoFactura')
            ElementTree.SubElement(xml_info_invoice, 'fechaEmision').text = datetime.strptime(date_joined, '%Y-%m-%d').strftime('%d/%m/%Y')
            ElementTree.SubElement(xml_info_invoice, 'dirEstablecimiento').text = company.get('establishment_address')
            ElementTree.SubElement(xml_info_invoice, 'obligadoContabilidad').text = company.get('obligated_accounting', 'NO')
            
            customer_identification = customer.get('identification')
            identification_type = '07'
            if customer_identification:
                if len(customer_identification) == 13:
                    identification_type = '04'
                elif len(customer_identification) == 10:
                    identification_type = '05'
                else:
                    customer_identification = '9999999999999'
            else:
                customer_identification = '9999999999999'
            
            ElementTree.SubElement(xml_info_invoice, 'tipoIdentificacionComprador').text = identification_type
            ElementTree.SubElement(xml_info_invoice, 'razonSocialComprador').text = customer.get('name', 'CONSUMIDOR FINAL')[:300]
            ElementTree.SubElement(xml_info_invoice, 'identificacionComprador').text = customer_identification
            ElementTree.SubElement(xml_info_invoice, 'direccionComprador').text = customer.get('address', 'N/A')
            ElementTree.SubElement(xml_info_invoice, 'totalSinImpuestos').text = f"{totals['subtotal']:.2f}"
            ElementTree.SubElement(xml_info_invoice, 'totalDescuento').text = f"{totals['total_discount']:.2f}"
            
            xml_total_with_taxes = ElementTree.SubElement(xml_info_invoice, 'totalConImpuestos')
            
            if totals['subtotal_without_tax'] > 0:
                subtotal_without_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
                ElementTree.SubElement(subtotal_without_tax, 'codigo').text = '2'
                ElementTree.SubElement(subtotal_without_tax, 'codigoPorcentaje').text = '0'
                ElementTree.SubElement(subtotal_without_tax, 'baseImponible').text = f"{totals['subtotal_without_tax']:.2f}"
                ElementTree.SubElement(subtotal_without_tax, 'valor').text = '0.00'
            
            if totals['subtotal_with_tax'] > 0:
                subtotal_with_tax = ElementTree.SubElement(xml_total_with_taxes, 'totalImpuesto')
                ElementTree.SubElement(subtotal_with_tax, 'codigo').text = '2'
                ElementTree.SubElement(subtotal_with_tax, 'codigoPorcentaje').text = str(company.get('tax_percentage', 4))
                ElementTree.SubElement(subtotal_with_tax, 'baseImponible').text = f"{totals['subtotal_with_tax']:.2f}"
                ElementTree.SubElement(subtotal_with_tax, 'valor').text = f"{totals['total_tax']:.2f}"
            
            ElementTree.SubElement(xml_info_invoice, 'propina').text = '0.00'
            ElementTree.SubElement(xml_info_invoice, 'importeTotal').text = f"{totals['total_amount']:.2f}"
            ElementTree.SubElement(xml_info_invoice, 'moneda').text = 'DOLAR'
            
            xml_payments = ElementTree.SubElement(xml_info_invoice, 'pagos')
            xml_payment = ElementTree.SubElement(xml_payments, 'pago')
            ElementTree.SubElement(xml_payment, 'formaPago').text = payment_method
            ElementTree.SubElement(xml_payment, 'total').text = f"{totals['total_amount']:.2f}"
            ElementTree.SubElement(xml_payment, 'plazo').text = '0' if payment_type == 'contado' else '30'
            ElementTree.SubElement(xml_payment, 'unidadTiempo').text = 'dias'
            
            xml_details = ElementTree.SubElement(root, 'detalles')
            for detail in details:
                xml_detail = ElementTree.SubElement(xml_details, 'detalle')
                ElementTree.SubElement(xml_detail, 'codigoPrincipal').text = detail['code']
                ElementTree.SubElement(xml_detail, 'descripcion').text = detail['name']
                ElementTree.SubElement(xml_detail, 'cantidad').text = f"{detail['quantity']:.2f}"
                ElementTree.SubElement(xml_detail, 'precioUnitario').text = f"{detail['price']:.2f}"
                ElementTree.SubElement(xml_detail, 'descuento').text = f"{detail['total_discount']:.2f}"
                ElementTree.SubElement(xml_detail, 'precioTotalSinImpuesto').text = f"{detail['total_amount']:.2f}"
                
                xml_taxes = ElementTree.SubElement(xml_detail, 'impuestos')
                xml_tax = ElementTree.SubElement(xml_taxes, 'impuesto')
                ElementTree.SubElement(xml_tax, 'codigo').text = '2'
                
                if detail['has_tax']:
                    ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = str(company.get('tax_percentage', 4))
                    ElementTree.SubElement(xml_tax, 'tarifa').text = f"{tax_rate * 100:.2f}"
                    ElementTree.SubElement(xml_tax, 'baseImponible').text = f"{detail['total_amount']:.2f}"
                    ElementTree.SubElement(xml_tax, 'valor').text = f"{detail['tax_amount']:.2f}"
                else:
                    ElementTree.SubElement(xml_tax, 'codigoPorcentaje').text = '0'
                    ElementTree.SubElement(xml_tax, 'tarifa').text = '0'
                    ElementTree.SubElement(xml_tax, 'baseImponible').text = f"{detail['total_amount']:.2f}"
                    ElementTree.SubElement(xml_tax, 'valor').text = '0'
            
            if additional_info:
                xml_additional = ElementTree.SubElement(root, 'infoAdicional')
                for info in additional_info:
                    ElementTree.SubElement(xml_additional, 'campoAdicional', nombre=info.get('name')).text = info.get('value')
            
            xml_string = ElementTree.tostring(root, xml_declaration=True, encoding='utf-8').decode('utf-8').replace("'", '"')
            
            return {'xml': xml_string}
            
        except Exception as e:
            return {'error': str(e)}
    
    def firm_xml(self, xml, signature_path, signature_key, receipt_number):
        try:
            import subprocess
            import os
            from tempfile import NamedTemporaryFile
            from pathlib import Path
            from config import settings
            
            with NamedTemporaryFile(suffix='.xml', delete=False) as file_temp:
                file_temp.write(xml.encode())
                file_temp.flush()
                file_temp_name = file_temp.name
                
                base_dir = os.path.dirname(os.path.dirname(__file__))
                jar_path = str(Path(os.path.join(base_dir, 'pos/files/jar/sri.jar')).absolute())
                certificate_path = str(Path(signature_path).absolute())
                xml_name = f'{receipt_number}.xml'
                output_dir = os.path.dirname(file_temp_name)
                
                commands = ['java', '-jar', jar_path, certificate_path, signature_key, file_temp_name, output_dir, xml_name]
                procedure = subprocess.run(args=commands, capture_output=True)
                
                if procedure.returncode == 0:
                    error = procedure.stdout.decode('utf-8')
                    if 'Error' in error:
                        return {'error': error}
                    else:
                        generated_xml_path = os.path.join(output_dir, xml_name)
                        if os.path.exists(generated_xml_path):
                            with open(generated_xml_path, 'rb') as file:
                                xml_signed = file.read().decode('utf-8')
                            os.remove(generated_xml_path)
                            return {'xml_signed': xml_signed}
                        else:
                            return {'error': 'No se generó el archivo firmado'}
                else:
                    return {'error': procedure.stderr.decode('utf-8')}
                    
        except Exception as e:
            return {'error': str(e)}
        finally:
            if 'file_temp_name' in locals() and os.path.exists(file_temp_name):
                os.remove(file_temp_name)
    
    def validate_xml_with_sri(self, xml, environment_type):
        try:
            import base64
            from suds.client import Client
            
            receipt_url = self.get_receipt_url(environment_type)
            
            document = xml.strip().encode('utf-8')
            base64_binary_xml = base64.b64encode(document).decode('utf-8')
            
            sri_client = Client(receipt_url)
            result = sri_client.service.validarComprobante(base64_binary_xml)
            
            status = result.estado
            
            if status == 'DEVUELTA':
                receipt = result.comprobantes.comprobante[0]
                errors = []
                for count, value in enumerate(receipt.mensajes):
                    message = value[1][count]
                    error_detail = {}
                    for name in ['identificador', 'informacionAdicional', 'mensaje', 'tipo']:
                        if name in message:
                            error_detail[name] = message[name]
                    errors.append(error_detail)
                
                return {
                    'resp': False,
                    'access_key': receipt.claveAcceso,
                    'errors': errors
                }
            elif status == 'RECIBIDA':
                return {'resp': True}
            
            return {'resp': False, 'errors': [{'mensaje': 'Estado desconocido del SRI'}]}
            
        except Exception as e:
            return {'resp': False, 'errors': [{'mensaje': str(e)}]}
    
    def authorize_xml_with_sri(self, access_code, environment_type):
        try:
            import time
            from suds.client import Client
            from lxml import etree
            
            authorization_url = self.get_authorization_url(environment_type)
            
            sri_client = Client(authorization_url)
            
            max_attempts = 3
            for attempt in range(max_attempts):
                if attempt > 0:
                    time.sleep(2)
                
                result = sri_client.service.autorizacionComprobante(access_code)
                
                if len(result):
                    receipt = result[2].autorizacion[0]
                    
                    if receipt.estado == 'NO AUTORIZADO':
                        errors = []
                        for count, value in enumerate(receipt.mensajes):
                            message = value[1][count]
                            error_detail = {}
                            for name in ['identificador', 'informacionAdicional', 'mensaje', 'tipo']:
                                if name in message:
                                    error_detail[name] = message[name]
                            errors.append(error_detail)
                        
                        return {
                            'resp': False,
                            'access_code': access_code,
                            'status': receipt.estado,
                            'authorization_date': str(receipt.fechaAutorizacion),
                            'errors': errors
                        }
                    elif receipt.estado == 'AUTORIZADO':
                        return {
                            'resp': True,
                            'authorization_number': receipt.numeroAutorizacion,
                            'authorization_date': str(receipt.fechaAutorizacion),
                            'status': receipt.estado
                        }
            
            return {
                'resp': False,
                'errors': [{'mensaje': f'No se pudo obtener autorización después de {max_attempts} intentos'}]
            }
            
        except Exception as e:
            return {'resp': False, 'errors': [{'mensaje': str(e)}]}
    
    def get_receipt_url(self, environment_type):
        if environment_type == 2:
            return 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
        return 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    
    def get_authorization_url(self, environment_type):
        if environment_type == 2:
            return 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
        return 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'

