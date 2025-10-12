using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace FacturadorSRI.DTOs
{
    public class InvoiceService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;

        public InvoiceService(string baseUrl = "http://localhost:8000/api")
        {
            _httpClient = new HttpClient();
            _baseUrl = baseUrl;
        }

        public async Task<InvoiceResponse> CreateInvoiceAsync(InvoiceRequest request)
        {
            var options = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            };

            var json = JsonSerializer.Serialize(request, options);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            
            var response = await _httpClient.PostAsync($"{_baseUrl}/invoice/create/", content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseContent = await response.Content.ReadAsStringAsync();
                return JsonSerializer.Deserialize<InvoiceResponse>(responseContent, options);
            }
            
            var errorContent = await response.Content.ReadAsStringAsync();
            throw new Exception($"Error al crear factura ({response.StatusCode}): {errorContent}");
        }
    }

    class Program
    {
        static async Task Main(string[] args)
        {
            var invoiceService = new InvoiceService();

            var request = new InvoiceRequest
            {
                Company = new CompanyData
                {
                    Ruc = "1234567890001",
                    CompanyName = "MI EMPRESA S.A.",
                    CommercialName = "MI EMPRESA",
                    MainAddress = "Av. Principal 123",
                    EstablishmentAddress = "Av. Principal 123",
                    ObligatedAccounting = "SI",
                    EnvironmentType = 1,
                    EmissionType = 1,
                    RetentionAgent = "NO",
                    RegimenRimpe = "CONTRIBUYENTE RÉGIMEN GENERAL",
                    IsPopularRegime = false,
                    TaxRate = 0.15m,
                    TaxPercentage = 4,
                    ElectronicSignaturePath = "/path/to/firma.p12",
                    ElectronicSignatureKey = "clave123"
                },
                Customer = new CustomerData
                {
                    Identification = "0123456789",
                    Name = "CLIENTE EJEMPLO",
                    Address = "Calle Secundaria 456",
                    Email = "cliente@example.com",
                    Phone = "0987654321"
                },
                Receipt = new ReceiptData
                {
                    VoucherType = "01",
                    EstablishmentCode = "001",
                    IssuingPointCode = "001",
                    ReceiptNumber = "000000123"
                },
                DateJoined = DateTime.Now.ToString("yyyy-MM-dd"),
                PaymentType = "contado",
                PaymentMethod = "01",
                CreateElectronicInvoice = true,
                AdditionalInfo = new List<AdditionalInfo>
                {
                    new AdditionalInfo { Name = "Email", Value = "cliente@example.com" },
                    new AdditionalInfo { Name = "Telefono", Value = "0987654321" }
                },
                Products = new List<ProductItem>
                {
                    new ProductItem 
                    { 
                        Code = "PROD001",
                        Name = "PRODUCTO EJEMPLO 1",
                        Quantity = 2, 
                        Price = 10.50m, 
                        Discount = 0,
                        HasTax = true
                    },
                    new ProductItem 
                    { 
                        Code = "PROD002",
                        Name = "PRODUCTO EJEMPLO 2",
                        Quantity = 1, 
                        Price = 25.00m, 
                        Discount = 10,
                        HasTax = true
                    }
                }
            };

            try
            {
                var response = await invoiceService.CreateInvoiceAsync(request);
                
                Console.WriteLine("=== FACTURA CREADA EXITOSAMENTE ===");
                Console.WriteLine($"Número: {response.ReceiptNumberFull}");
                Console.WriteLine($"Clave de Acceso: {response.AccessCode}");
                Console.WriteLine($"Subtotal: ${response.Subtotal:F2}");
                Console.WriteLine($"IVA: ${response.TotalTax:F2}");
                Console.WriteLine($"Total: ${response.TotalAmount:F2}");
                
                if (!string.IsNullOrEmpty(response.Xml))
                {
                    Console.WriteLine("\n=== XML GENERADO ===");
                    Console.WriteLine("XML generado correctamente");
                }
                
                if (!string.IsNullOrEmpty(response.XmlSigned))
                {
                    Console.WriteLine("\n=== XML FIRMADO ===");
                    Console.WriteLine("XML firmado correctamente");
                }
                
                if (response.SriValidation != null)
                {
                    Console.WriteLine("\n=== VALIDACIÓN SRI ===");
                    Console.WriteLine($"Estado: {response.SriValidation.Status}");
                    Console.WriteLine($"Mensaje: {response.SriValidation.Message}");
                    
                    if (response.SriValidation.Errors != null && response.SriValidation.Errors.Count > 0)
                    {
                        Console.WriteLine("\nErrores de validación:");
                        foreach (var error in response.SriValidation.Errors)
                        {
                            Console.WriteLine($"- [{error.Tipo}] {error.Mensaje}");
                            if (!string.IsNullOrEmpty(error.InformacionAdicional))
                            {
                                Console.WriteLine($"  Info: {error.InformacionAdicional}");
                            }
                        }
                    }
                }
                
                if (response.SriAuthorization != null)
                {
                    Console.WriteLine("\n=== AUTORIZACIÓN SRI ===");
                    Console.WriteLine($"Estado: {response.SriAuthorization.Status}");
                    Console.WriteLine($"Mensaje: {response.SriAuthorization.Message}");
                    
                    if (response.SriAuthorization.Status == "AUTORIZADO")
                    {
                        Console.WriteLine($"Número Autorización: {response.SriAuthorization.AuthorizationNumber}");
                        Console.WriteLine($"Fecha Autorización: {response.SriAuthorization.AuthorizationDate}");
                    }
                    
                    if (response.SriAuthorization.Errors != null && response.SriAuthorization.Errors.Count > 0)
                    {
                        Console.WriteLine("\nErrores de autorización:");
                        foreach (var error in response.SriAuthorization.Errors)
                        {
                            Console.WriteLine($"- [{error.Tipo}] {error.Mensaje}");
                        }
                    }
                }
                
                if (!string.IsNullOrEmpty(response.ElectronicError))
                {
                    Console.WriteLine($"\n⚠️ Error Electrónico: {response.ElectronicError}");
                }
                
                Console.WriteLine("\n=== DETALLES ===");
                foreach (var detail in response.Details)
                {
                    Console.WriteLine($"{detail.Name} x{detail.Quantity} - ${detail.TotalAmount:F2}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR: {ex.Message}");
            }
        }
    }
}
