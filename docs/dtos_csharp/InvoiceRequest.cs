using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace FacturadorSRI.DTOs
{
    public class InvoiceRequest
    {
        [JsonPropertyName("company")]
        public CompanyData Company { get; set; }

        [JsonPropertyName("customer")]
        public CustomerData Customer { get; set; }

        [JsonPropertyName("receipt")]
        public ReceiptData Receipt { get; set; }

        [JsonPropertyName("date_joined")]
        public string DateJoined { get; set; }

        [JsonPropertyName("payment_type")]
        public string PaymentType { get; set; }

        [JsonPropertyName("payment_method")]
        public string PaymentMethod { get; set; }

        [JsonPropertyName("create_electronic_invoice")]
        public bool CreateElectronicInvoice { get; set; }

        [JsonPropertyName("additional_info")]
        public List<AdditionalInfo> AdditionalInfo { get; set; }

        [JsonPropertyName("products")]
        public List<ProductItem> Products { get; set; }
    }

    public class CompanyData
    {
        [JsonPropertyName("ruc")]
        public string Ruc { get; set; }

        [JsonPropertyName("company_name")]
        public string CompanyName { get; set; }

        [JsonPropertyName("commercial_name")]
        public string CommercialName { get; set; }

        [JsonPropertyName("main_address")]
        public string MainAddress { get; set; }

        [JsonPropertyName("establishment_address")]
        public string EstablishmentAddress { get; set; }

        [JsonPropertyName("obligated_accounting")]
        public string ObligatedAccounting { get; set; }

        [JsonPropertyName("environment_type")]
        public int EnvironmentType { get; set; }

        [JsonPropertyName("emission_type")]
        public int EmissionType { get; set; }

        [JsonPropertyName("retention_agent")]
        public string RetentionAgent { get; set; }

        [JsonPropertyName("regimen_rimpe")]
        public string RegimenRimpe { get; set; }

        [JsonPropertyName("is_popular_regime")]
        public bool IsPopularRegime { get; set; }

        [JsonPropertyName("tax_rate")]
        public decimal TaxRate { get; set; }

        [JsonPropertyName("tax_percentage")]
        public int TaxPercentage { get; set; }

        [JsonPropertyName("electronic_signature_path")]
        public string ElectronicSignaturePath { get; set; }

        [JsonPropertyName("electronic_signature_key")]
        public string ElectronicSignatureKey { get; set; }
    }

    public class CustomerData
    {
        [JsonPropertyName("identification")]
        public string Identification { get; set; }

        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("address")]
        public string Address { get; set; }

        [JsonPropertyName("email")]
        public string Email { get; set; }

        [JsonPropertyName("phone")]
        public string Phone { get; set; }
    }

    public class ReceiptData
    {
        [JsonPropertyName("voucher_type")]
        public string VoucherType { get; set; }

        [JsonPropertyName("establishment_code")]
        public string EstablishmentCode { get; set; }

        [JsonPropertyName("issuing_point_code")]
        public string IssuingPointCode { get; set; }

        [JsonPropertyName("receipt_number")]
        public string ReceiptNumber { get; set; }
    }

    public class AdditionalInfo
    {
        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("value")]
        public string Value { get; set; }
    }

    public class ProductItem
    {
        [JsonPropertyName("code")]
        public string Code { get; set; }

        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("quantity")]
        public int Quantity { get; set; }

        [JsonPropertyName("price")]
        public decimal Price { get; set; }

        [JsonPropertyName("discount")]
        public decimal Discount { get; set; }

        [JsonPropertyName("has_tax")]
        public bool HasTax { get; set; }
    }
}
