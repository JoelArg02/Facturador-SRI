// Map codes defined by el SRI to real VAT percentage values
const TAX_PERCENTAGE_VALUE_MAP = {
  '0': 0,
  '2': 12,
  '3': 14,
  '4': 15,
  '5': 5,
  '6': 0,
  '7': 0,
  '8': 0,
  '10': 13,
};

function resolveTaxValue(code) {
  const normalized = code !== undefined && code !== null ? String(code) : undefined;
  if (normalized && Object.prototype.hasOwnProperty.call(TAX_PERCENTAGE_VALUE_MAP, normalized)) {
    return TAX_PERCENTAGE_VALUE_MAP[normalized];
  }
  return 0;
}

// Onboarding form handler
class OnboardingForm {
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 5;
    this.init();
  }

  init() {
    this.showStep(this.currentStep);
    this.bindEvents();
    this.setupFieldValidation();
    this.setupSpecialTaxpayerLogic();
    this.handleExistingErrors();
  }

  showStep(step) {
    // Hide all steps
    document.querySelectorAll('.form-step').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));

    // Show current step
    document.querySelector(`.form-step[data-step="${step}"]`).classList.add('active');

    // Update progress
    for (let i = 1; i <= this.totalSteps; i++) {
      const stepEl = document.querySelector(`.step[data-step="${i}"]`);
      if (i < step) {
        stepEl.classList.add('completed');
      } else if (i === step) {
        stepEl.classList.add('active');
      }
    }

    // Update navigation buttons
    this.updateNavigationButtons(step);
  }

  updateNavigationButtons(step) {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');

    prevBtn.style.display = step > 1 ? 'flex' : 'none';
    nextBtn.style.display = step < this.totalSteps ? 'flex' : 'none';
    submitBtn.style.display = step === this.totalSteps ? 'flex' : 'none';
  }

  validateStep(step) {
    const stepEl = document.querySelector(`.form-step[data-step="${step}"]`);
    const requiredFields = stepEl.querySelectorAll('input[required], select[required]');
    let isValid = true;
    let firstInvalidField = null;

    // Limpiar errores previos del paso actual
    stepEl.querySelectorAll('.field-group').forEach(group => {
      group.classList.remove('has-error');
    });

    // Validar cada campo requerido
    for (let field of requiredFields) {
      if (!field.value.trim()) {
        const fieldGroup = field.closest('.field-group');
        if (fieldGroup) {
          fieldGroup.classList.add('has-error');
          if (!firstInvalidField) {
            firstInvalidField = field;
          }
        }
        isValid = false;
      }
    }

    // Validación especial para contribuyente especial en el paso 3
    if (step === 3) {
      const isSpecialTaxpayer = document.getElementById('is_special_taxpayer');
      const specialTaxpayerNumber = document.getElementById('special_taxpayer_number');
      
      if (isSpecialTaxpayer && isSpecialTaxpayer.value === 'yes') {
        if (!specialTaxpayerNumber || !specialTaxpayerNumber.value.trim()) {
          const fieldGroup = specialTaxpayerNumber.closest('.field-group');
          if (fieldGroup) {
            fieldGroup.classList.add('has-error');
            if (!firstInvalidField) {
              firstInvalidField = specialTaxpayerNumber;
            }
          }
          isValid = false;
        }
      }
    }

    // Si hay errores, enfocar el primer campo inválido
    if (!isValid && firstInvalidField) {
      firstInvalidField.focus();
      firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    return isValid;
  }

  bindEvents() {
    const nextBtn = document.getElementById('nextBtn');
    const prevBtn = document.getElementById('prevBtn');
    const form = document.querySelector('.onboarding-form');

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.validateStep(this.currentStep)) {
          if (this.currentStep < this.totalSteps) {
            this.currentStep++;
            this.showStep(this.currentStep);
          }
        }
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentStep > 1) {
          this.currentStep--;
          this.showStep(this.currentStep);
        }
      });
    }

    if (form) {
      form.addEventListener('submit', (e) => {
        this.handleFormSubmission(e);
      });
    }
  }

  setupFieldValidation() {
    const requiredFields = [
      'id_ruc', 'id_company_name', 'id_commercial_name', 'id_main_address',
      'id_establishment_code', 'id_issuing_point_code', 'id_email'
    ];

    requiredFields.forEach(fieldId => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.setAttribute('required', 'required');
      }
    });

    // Agregar validación en tiempo real
    const allFields = document.querySelectorAll('input, select');
    allFields.forEach(field => {
      field.addEventListener('input', function () {
        const fieldGroup = this.closest('.field-group');
        if (fieldGroup && fieldGroup.classList.contains('has-error')) {
          if (this.value.trim()) {
            fieldGroup.classList.remove('has-error');
          }
        }
      });

      field.addEventListener('blur', function () {
        if (this.hasAttribute('required') && !this.value.trim()) {
          const fieldGroup = this.closest('.field-group');
          if (fieldGroup) {
            fieldGroup.classList.add('has-error');
          }
        }
      });
    });
  }

  setupSpecialTaxpayerLogic() {
    const isSpecialTaxpayerSelect = document.getElementById('is_special_taxpayer');
    const specialTaxpayerNumberGroup = document.getElementById('special_taxpayer_number_group');
    const specialTaxpayerNumberInput = document.getElementById('special_taxpayer_number');
    const hiddenSpecialTaxpayerField = document.getElementById('id_special_taxpayer');

    if (isSpecialTaxpayerSelect && specialTaxpayerNumberGroup && specialTaxpayerNumberInput && hiddenSpecialTaxpayerField) {
      // Mostrar/ocultar campo de número de resolución
      isSpecialTaxpayerSelect.addEventListener('change', function() {
        if (this.value === 'yes') {
          specialTaxpayerNumberGroup.style.display = 'flex';
          specialTaxpayerNumberInput.setAttribute('required', 'required');
          // Si no hay valor, dejar vacío para que el usuario lo llene
          if (!specialTaxpayerNumberInput.value) {
            hiddenSpecialTaxpayerField.value = '';
          }
        } else {
          // No es contribuyente especial: usar 000
          specialTaxpayerNumberGroup.style.display = 'none';
          specialTaxpayerNumberInput.removeAttribute('required');
          specialTaxpayerNumberInput.value = '000';
          hiddenSpecialTaxpayerField.value = '000';
        }
      });

      // Copiar valor al campo oculto cuando se escriba
      specialTaxpayerNumberInput.addEventListener('input', function() {
        hiddenSpecialTaxpayerField.value = this.value;
      });

      // Inicializar el campo oculto basado en el valor actual
      if (hiddenSpecialTaxpayerField.value && hiddenSpecialTaxpayerField.value.trim() !== '') {
        if (hiddenSpecialTaxpayerField.value === '000') {
          // No es contribuyente especial
          isSpecialTaxpayerSelect.value = 'no';
          specialTaxpayerNumberGroup.style.display = 'none';
          specialTaxpayerNumberInput.value = '000';
        } else {
          // Es contribuyente especial con número real
          isSpecialTaxpayerSelect.value = 'yes';
          specialTaxpayerNumberGroup.style.display = 'flex';
          specialTaxpayerNumberInput.value = hiddenSpecialTaxpayerField.value;
          specialTaxpayerNumberInput.setAttribute('required', 'required');
        }
      } else {
        // Valor por defecto: no es contribuyente especial
        isSpecialTaxpayerSelect.value = 'no';
        specialTaxpayerNumberInput.value = '000';
        hiddenSpecialTaxpayerField.value = '000';
      }
    }
  }

  handleExistingErrors() {
    // Procesar errores de campos individuales
    const fieldGroups = document.querySelectorAll('.field-group');
    fieldGroups.forEach(group => {
      const errorDiv = group.querySelector('.error');
      if (errorDiv) {
        group.classList.add('has-error');
      }
    });

    // Mostrar errores de validación si existen
    const errorBox = document.querySelector('.error-box');
    if (errorBox) {
      errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Destacar el error por un momento
      setTimeout(() => {
        errorBox.style.animation = 'pulse 0.5s ease-in-out 3';
      }, 500);
    }

    // Si hay errores de campo, hacer scroll al primer campo con error
    const firstErrorField = document.querySelector('.field-group.has-error');
    if (firstErrorField && !errorBox) {
      firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Determinar en qué paso está el error
      let errorStep = 1;
      const formSteps = document.querySelectorAll('.form-step');
      formSteps.forEach((step, index) => {
        if (step.contains(firstErrorField)) {
          errorStep = index + 1;
        }
      });

      // Cambiar al paso con error
      if (errorStep !== this.currentStep) {
        this.currentStep = errorStep;
        this.showStep(this.currentStep);
      }
    }
  }

  handleFormSubmission(event) {
    console.log('Form submission started');

    // Actualizar establishment_address con main_address si está vacío
    const mainAddress = document.getElementById('id_main_address');
    const establishmentAddress = document.getElementById('id_establishment_address');
    if (mainAddress && establishmentAddress) {
      establishmentAddress.value = mainAddress.value;
    }

    // Sincronizar tax con tax_percentage
    const taxPercentage = document.getElementById('id_tax_percentage');
    const tax = document.getElementById('id_tax');
    if (taxPercentage && tax) {
      const syncTaxValue = () => {
        const resolved = resolveTaxValue(taxPercentage.value);
        tax.value = resolved !== undefined ? resolved : 0;
      };

      // Valor inicial
      syncTaxValue();

      // Sincronizar cuando cambie tax_percentage
      taxPercentage.addEventListener('input', syncTaxValue);
      taxPercentage.addEventListener('change', syncTaxValue);
    }

    // Log form data for debugging
    const formData = new FormData(event.target);
    console.log('Form data:');
    for (let [key, value] of formData.entries()) {
      console.log(`${key}: ${value}`);
    }
  }
}

// Initialize the onboarding form when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  new OnboardingForm();
});