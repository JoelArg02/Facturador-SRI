$(function () {
    console.log('[Company Form] Inicializando...');
    
    // Verificar si ya existe una firma electrónica guardada
    var hasExistingSignature = $('.alert-success').length > 0 && $('.alert-success').text().indexOf('Firma electrónica actual') !== -1;
    console.log('[Company Form] ¿Tiene firma guardada?', hasExistingSignature);
    
    // Inicializar Select2 en campos select
    $('select').each(function() {
        $(this).select2({
            theme: 'bootstrap4',
            language: 'es',
            width: '100%'
        });
    });

    // Copiar dirección matriz a establecimiento
    var $mainAddress = $('textarea[name="main_address"]');
    var $establishmentAddress = $('textarea[name="establishment_address"]');
    
    if ($mainAddress.length && $establishmentAddress.length) {
        $mainAddress.on('blur', function() {
            if (!$establishmentAddress.val()) {
                $establishmentAddress.val($(this).val());
            }
        });
    }

    // FormValidation
    console.log('[FormValidation] Configurando validación...');
    
    // Configurar campos de validación
    var validationFields = {
        ruc: {
            validators: {
                notEmpty: {
                    message: 'El RUC es obligatorio'
                },
                stringLength: {
                    min: 10,
                    max: 13,
                    message: 'El RUC debe tener entre 10 y 13 dígitos'
                }
            }
        },
        company_name: {
            validators: {
                notEmpty: {
                    message: 'La razón social es obligatoria'
                }
            }
        },
        commercial_name: {
            validators: {
                notEmpty: {
                    message: 'El nombre comercial es obligatorio'
                }
            }
        },
        main_address: {
            validators: {
                notEmpty: {
                    message: 'La dirección matriz es obligatoria'
                }
            }
        },
        establishment_address: {
            validators: {
                notEmpty: {
                    message: 'La dirección del establecimiento es obligatoria'
                }
            }
        },
        establishment_code: {
            validators: {
                notEmpty: {
                    message: 'El código de establecimiento es obligatorio'
                }
            }
        },
        issuing_point_code: {
            validators: {
                notEmpty: {
                    message: 'El código de punto de emisión es obligatorio'
                }
            }
        },
        obligated_accounting: {
            validators: {
                notEmpty: {
                    message: 'Debe indicar si está obligado a llevar contabilidad'
                }
            }
        },
        retention_agent: {
            validators: {
                notEmpty: {
                    message: 'Debe indicar si es agente de retención'
                }
            }
        },
        regimen_rimpe: {
            validators: {
                notEmpty: {
                    message: 'Debe indicar si pertenece al régimen RIMPE'
                }
            }
        },
        environment_type: {
            validators: {
                notEmpty: {
                    message: 'El tipo de ambiente es obligatorio'
                }
            }
        },
        emission_type: {
            validators: {
                notEmpty: {
                    message: 'El tipo de emisión es obligatorio'
                }
            }
        },
        tax_percentage: {
            validators: {
                notEmpty: {
                    message: 'El porcentaje de IVA es obligatorio'
                }
            }
        },
        email: {
            validators: {
                notEmpty: {
                    message: 'El email es obligatorio'
                },
                emailAddress: {
                    message: 'El email no es válido'
                }
            }
        },
        mobile: {
            validators: {
                notEmpty: {
                    message: 'El celular es obligatorio'
                }
            }
        }
    };
    
    // Solo hacer obligatoria la firma electrónica si NO existe una guardada
    if (!hasExistingSignature) {
        console.log('[FormValidation] Firma NO guardada, será obligatoria');
        validationFields.electronic_signature = {
            validators: {
                notEmpty: {
                    message: 'La firma electrónica es obligatoria'
                },
                file: {
                    extension: 'p12',
                    message: 'El archivo debe tener extensión .p12'
                }
            }
        };
        validationFields.electronic_signature_key = {
            validators: {
                notEmpty: {
                    message: 'La contraseña de la firma es obligatoria'
                }
            }
        };
    } else {
        console.log('[FormValidation] Firma YA guardada, será opcional');
    }
    
    var fv = FormValidation.formValidation(
        document.getElementById('frmForm'),
        {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            fields: validationFields,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh'
                }),
            },
        }
    ).on('core.form.valid', function() {
        console.log('[FormValidation] ✅ Formulario válido, enviando...');
        
        var formData = new FormData($('#frmForm')[0]);
        
        submit_with_formdata({
            type: 'blue',
            theme: 'modern',
            title: 'Confirmación',
            icon: 'fas fa-info-circle',
            content: '¿Está seguro de guardar los cambios?',
            form: '#frmForm',
            pathname: window.location.href,
            params: formData,
            success: function(response) {
                console.log('[Submit Success] Respuesta:', response);
                
                // Mostrar mensaje de éxito con SweetAlert
                alert_sweetalert({
                    type: 'success',
                    title: '¡Éxito!',
                    message: 'Los datos se guardaron correctamente',
                    timer: 2000,
                    callback: function() {
                        // Recargar para ver los cambios
                        location.reload();
                    }
                });
            }
        });
    }).on('core.form.invalid', function() {
        console.log('[FormValidation] ❌ Formulario inválido');
        message_error('Por favor corrija los errores en el formulario');
    });

    console.log('[Company Form] ✅ Inicialización completa');
});
