using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace FacturadorSRI.DTOs
{
    public class InvoiceResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("receipt_number_full")]
        public string ReceiptNumberFull { get; set; }

        [JsonPropertyName("access_code")]
        public string AccessCode { get; set; }

        [JsonPropertyName("subtotal")]
        public decimal Subtotal { get; set; }

        [JsonPropertyName("subtotal_with_tax")]
        public decimal SubtotalWithTax { get; set; }

        [JsonPropertyName("subtotal_without_tax")]
        public decimal SubtotalWithoutTax { get; set; }

        [JsonPropertyName("total_discount")]
        public decimal TotalDiscount { get; set; }

        [JsonPropertyName("total_tax")]
        public decimal TotalTax { get; set; }

        [JsonPropertyName("total_amount")]
        public decimal TotalAmount { get; set; }

        [JsonPropertyName("details")]
        public List<InvoiceDetailResponse> Details { get; set; }

        [JsonPropertyName("xml")]
        public string Xml { get; set; }

        [JsonPropertyName("xml_signed")]
        public string XmlSigned { get; set; }

        [JsonPropertyName("sri_validation")]
        public SriValidationData SriValidation { get; set; }

        [JsonPropertyName("sri_authorization")]
        public SriAuthorizationData SriAuthorization { get; set; }

        [JsonPropertyName("electronic_error")]
        public string ElectronicError { get; set; }
    }

    public class InvoiceDetailResponse
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

        [JsonPropertyName("total_discount")]
        public decimal TotalDiscount { get; set; }

        [JsonPropertyName("total_amount")]
        public decimal TotalAmount { get; set; }

        [JsonPropertyName("tax_amount")]
        public decimal TaxAmount { get; set; }

        [JsonPropertyName("has_tax")]
        public bool HasTax { get; set; }
    }

    public class SriValidationData
    {
        [JsonPropertyName("status")]
        public string Status { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; }

        [JsonPropertyName("errors")]
        public List<SriError> Errors { get; set; }
    }

    public class SriAuthorizationData
    {
        [JsonPropertyName("status")]
        public string Status { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; }

        [JsonPropertyName("authorization_number")]
        public string AuthorizationNumber { get; set; }

        [JsonPropertyName("authorization_date")]
        public string AuthorizationDate { get; set; }

        [JsonPropertyName("errors")]
        public List<SriError> Errors { get; set; }
    }

    public class SriError
    {
        [JsonPropertyName("identificador")]
        public string Identificador { get; set; }

        [JsonPropertyName("mensaje")]
        public string Mensaje { get; set; }

        [JsonPropertyName("tipo")]
        public string Tipo { get; set; }

        [JsonPropertyName("informacionAdicional")]
        public string InformacionAdicional { get; set; }
    }
}
