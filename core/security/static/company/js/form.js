var fv;

document.addEventListener('DOMContentLoaded', function () {
    fv = FormValidation.formValidation(document.getElementById('frmForm'), {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                excluded: new FormValidation.plugins.Excluded(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh'
                })
            },
            fields: {
                ruc: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 13,
                            max: 13
                        }
                    }
                },
                company_name: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 2
                        }
                    }
                },
                commercial_name: {
                    validators: {
                        notEmpty: {},
                        stringLength: {
                            min: 2
                        }
                    }
                },
                email: {
                    validators: {
                        notEmpty: {},
                        emailAddress: {}
                    }
                },
                electronic_signature: {
                    validators: {
                        file: {
                            extension: 'p12,pfx',
                            type: 'application/x-pkcs12',
                            maxFiles: 1
                        }
                    }
                },
                image: {
                    validators: {
                        file: {
                            extension: 'jpeg,jpg,png',
                            type: 'image/jpeg,image/png',
                            maxFiles: 1
                        }
                    }
                }
            }
        }
    )
        .on('core.element.validated', function (e) {
            if (e.valid) {
                const groupEle = FormValidation.utils.closest(e.element, '.form-group');
                if (groupEle) {
                    FormValidation.utils.classSet(groupEle, {
                        'has-success': false
                    });
                }
                FormValidation.utils.classSet(e.element, {
                    'is-valid': false
                });
            }
            const iconPlugin = fv.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            if (iconElement) {
                iconElement.style.display = 'none';
            }
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(fv.form.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach(function (messageEle) {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            var args = {
                params: new FormData(fv.form),
                form: fv.form
            };
            submit_with_formdata(args);
        });
});
