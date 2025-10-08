using System.Text.Json.Serialization;

namespace FacturadorSRI.DTOs
{
    public class ApiErrorResponse
    {
        [JsonPropertyName("error")]
        public string Error { get; set; }
    }
}
