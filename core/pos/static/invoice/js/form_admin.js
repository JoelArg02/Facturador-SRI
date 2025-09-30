var fv;
var select_customer, select_receipt, select_payment_type;
var input_search_product, input_date_joined, input_end_credit, input_cash, input_change, input_transaction;
var tblProducts, tblSearchProducts, tblAdditionalInfo;

var invoice = {
    detail: {
        tax: 0.00,
        subtotal_without_tax: 0.00,
        subtotal_with_tax: 0.00,
        total_discount: 0.00,
        subtotal: 0.00,
        total_tax: 0.00,
        total_amount: 0.00,
        products: [],
        additional_info: [],
    },
    addProduct: function (item) {
        var index = this.detail.products.findIndex(value => value.code === item.code);
        if (index === -1) {
            this.detail.products.push(item);
        } else {
            var product = this.detail.products[index];
            product.quantity += 1;
        }
        this.listProducts();
    },
    getProductId: function () {
        return this.detail.products.map(value => value.id);
    },
    listProducts: function () {
        this.totalCalculator();
        tblProducts = $('#tblProducts').DataTable({
            autoWidth: false,
            destroy: true,
            data: this.detail.products,
            // ordering: false,
            lengthChange: false,
            searching: false,
            paginate: false,
            columns: [
                {data: "id"},
                {data: "code"},
                {data: "name"},
                {data: "stock"},
                {data: "quantity"},
                {data: "current_price"},
                {data: "total_discount"},
                {data: "total_amount"},
            ],
            columnDefs: [
                {
                    targets: [-5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.is_inventoried) {
                            if (row.stock > 0) {
                                return '<span class="badge badge-success badge-pill">' + row.stock + '</span>';
                            }
                            return '<span class="badge badge-danger badge-pill">' + row.stock + '</span>';
                        }
                        return '<span class="badge badge-secondary badge-pill">Sin stock</span>';
                    }
                },
                {
                    targets: [-4],
                    class: 'text-center',
                    width: '20%',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="quantity" min="1" max="1000000" data-decimals="0" step="1" value="' + row.quantity + '">';
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="current_price" value="' + row.current_price + '">';
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    width: '20%',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="discount" value="' + row.discount + '">';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(2);
                    }
                },
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="remove" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-times"></i></a>';
                    }
                },
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                tr.find('input[name="quantity"]')
                    .TouchSpin({
                        min: 1,
                        max: data.is_inventoried ? data.stock : 1000000
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'numbers'});
                    });

                tr.find('input[name="current_price"]')
                    .TouchSpin({
                        min: 0.0000,
                        max: 1000000,
                        step: 0.0001,
                        decimals: 4,
                        boostat: 5,
                        maxboostedstep: 10
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'decimals'});
                    });

                tr.find('input[name="discount"]')
                    .TouchSpin({
                        min: 0.00,
                        max: 100,
                        step: 0.01,
                        decimals: 2,
                        boostat: 5,
                        maxboostedstep: 10,
                        postfix: "0.00"
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'decimals'});
                    });
            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    },
    listAdditionalInfo: function () {
        tblAdditionalInfo = $('#tblAdditionalInfo').DataTable({
            autoWidth: false,
            destroy: true,
            data: this.detail.additional_info,
            ordering: false,
            lengthChange: false,
            searching: false,
            paginate: false,
            info: false,
            columns: [
                {data: "name"},
                {data: "name"},
                {data: "value"},
            ],
            columnDefs: [
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" placeholder="Ingrese un nombre" autocomplete="off" name="additional_info_name" value="' + row.name + '">';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" placeholder="Ingrese un valor" autocomplete="off" name="additional_info_value" value="' + row.value + '">';
                    }
                },
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="remove" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-times"></i></a>';
                    }
                },
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    },
    toggleInputVisibility: function (inputs) {
        inputs.forEach(function (value, index, array) {
            if (value.enable) {
                $(input_transaction[value.index]).removeClass('d-none');
            } else {
                $(input_transaction[value.index]).addClass('d-none');
            }
        });
    },
    totalCalculator: function () {
        var tax = this.detail.tax / 100;
        this.detail.products.forEach(function (value, index, array) {
            value.tax = parseFloat(tax);
            value.price_with_tax = value.current_price + (value.current_price * value.tax);
            value.subtotal = value.current_price * value.quantity;
            value.total_discount = value.subtotal * parseFloat((value.discount / 100));
            value.total_tax = (value.subtotal - value.total_discount) * value.tax;
            value.total_amount = value.subtotal - value.total_discount;
        });

        this.detail.subtotal_without_tax = this.detail.products.filter(value => !value.has_tax).reduce((a, b) => a + (b.total_amount || 0), 0);
        this.detail.subtotal_with_tax = this.detail.products.filter(value => value.has_tax).reduce((a, b) => a + (b.total_amount || 0), 0);
        this.detail.total_discount = this.detail.products.reduce((a, b) => a + (b.total_discount || 0), 0);
        this.detail.subtotal = parseFloat(this.detail.subtotal_without_tax) + parseFloat(this.detail.subtotal_with_tax);
        this.detail.total_tax = parseFloat(this.detail.products.filter(value => value.has_tax).reduce((a, b) => a + (b.total_tax || 0), 0).toFixed(3));
        this.detail.total_amount = (Math.round(this.detail.subtotal * 100) / 100) + (Math.round(this.detail.total_tax * 100) / 100);

        $('input[name="subtotal_without_tax"]').val(this.detail.subtotal_without_tax.toFixed(2));
        $('input[name="subtotal_with_tax"]').val(this.detail.subtotal_with_tax.toFixed(2));
        $('input[name="tax"]').val(this.detail.tax.toFixed(2));
        $('input[name="total_tax"]').val(this.detail.total_tax.toFixed(2));
        $('input[name="total_discount"]').val(this.detail.total_discount.toFixed(2));
        $('input[name="total_amount"]').val(this.detail.total_amount.toFixed(2));
    },
    validateChange: function () {
        var is_draft_invoice = $('input[name="is_draft_invoice"]').is(':checked');
        if (is_draft_invoice && select_receipt.val() === '01') {
            return {valid: true};
        }
        var cash = parseFloat(input_cash.val());
        var totalAmount = invoice.detail.total_amount;

        if (isNaN(cash) || cash < 0) {
            input_change.val('0.00');
            return {valid: false, message: 'Ingrese un monto válido en efectivo'};
        }

        if (select_payment_type.val() === 'efectivo' && cash < totalAmount) {
            input_change.val('0.00');
            return {valid: false, message: 'El efectivo debe ser mayor o igual al total a pagar'};
        }

        var change = cash - totalAmount;
        input_change.val(change.toFixed(2));
        return {valid: true};
    }
};

document.addEventListener('DOMContentLoaded', function (e) {
    fv = FormValidation.formValidation(document.getElementById('frmForm'), {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                // excluded: new FormValidation.plugins.Excluded(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                customer: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione un cliente'
                        }
                    }
                },
                date_joined: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                            message: 'La fecha es obligatoria'
                        },
                        date: {
                            format: 'YYYY-MM-DD',
                            message: 'La fecha no es válida'
                        }
                    }
                },
                end_credit: {
                    validators: {
                        notEmpty: {
                            enabled: false,
                            message: 'La fecha es obligatoria'
                        },
                        date: {
                            format: 'YYYY-MM-DD',
                            message: 'La fecha no es válida'
                        }
                    }
                },
                receipt_number: {
                    validators: {
                        notEmpty: {}
                    }
                },
                cash: {
                    validators: {
                        notEmpty: {},
                        numeric: {
                            message: 'El valor no es un número',
                            thousandsSeparator: '',
                            decimalSeparator: '.'
                        }
                    }
                },
                change: {
                    validators: {
                        notEmpty: {},
                        callback: {
                            message: 'El cambio no puede ser negativo',
                            callback: function (input) {
                                return invoice.validateChange();
                            }
                        }
                    }
                },
            },
        }
    )
        .on('core.element.validated', function (e) {
            if (e.valid) {
                const groupEle = FormValidation.utils.closest(e.element, '.form-group');
                if (groupEle) {
                    FormValidation.utils.classSet(groupEle, {
                        'has-success': false,
                    });
                }
                FormValidation.utils.classSet(e.element, {
                    'is-valid': false,
                });
            }
            const iconPlugin = fv.getPlugin('icon');
            const iconElement = iconPlugin && iconPlugin.icons.has(e.element) ? iconPlugin.icons.get(e.element) : null;
            iconElement && (iconElement.style.display = 'none');
        })
        .on('core.validator.validated', function (e) {
            if (!e.result.valid) {
                const messages = [].slice.call(fv.form.querySelectorAll('[data-field="' + e.field + '"][data-validator]'));
                messages.forEach((messageEle) => {
                    const validator = messageEle.getAttribute('data-validator');
                    messageEle.style.display = validator === e.validator ? 'block' : 'none';
                });
            }
        })
        .on('core.form.valid', function () {
            if (invoice.detail.products.length === 0) {
                return message_error('Debe tener al menos un item en el detalle de la venta');
            }
            var customer = select_customer.select2('data')[0];
            if (select_receipt.val() === '1') {
                if (customer.identification_type.id === '07' && invoice.detail.total >= 50.00) {
                    return message_error('No se puede facturar un monto de 50 dólares con un cliente consumidor final');
                }
                if (customer.identification_type.id === '07' && select_payment_type.val() === 'credito') {
                    return message_error('No se puede facturar a crédito con un cliente consumidor final');
                }
            }
            var href_url = $(fv.form).attr('data-url');
            var params = new FormData(fv.form);
            params.append('products', JSON.stringify(invoice.detail.products));
            params.append('additional_info', JSON.stringify(invoice.detail.additional_info.filter(value => !$.isEmptyObject(value.name) && !$.isEmptyObject(value.value))));
            var args = {
                'params': params,
                'success': function (request) {
                    dialog_action({
                        'content': '¿Desea Imprimir el Comprobante?',
                        'success': function () {
                            window.open(request.print_url, '_blank');
                            location.href = href_url;
                        },
                        'cancel': function () {
                            location.href = href_url;
                        }
                    });
                }
            };
            submit_with_formdata(args);
        });
});

$(function () {
    select_customer = $('select[name="customer"]');
    select_receipt = $('select[name="receipt"]');
    // Fix: selector roto (faltaba "]"). Esto rompía el JS e impedía inicializar el buscador de productos
    select_payment_type = $('select[name="payment_type"]');
    input_search_product = $('input[name="search"]');
    input_date_joined = $('input[name="date_joined"]');
    input_end_credit = $('input[name="end_credit"]');
    input_cash = $('input[name="cash"]');
    input_change = $('input[name="change"]');
    input_transaction = $('.content-transaction > div.form-input');

    $('.select2').select2({
        theme: 'bootstrap4',
        language: 'es',
    });

    // Customer

    select_customer.select2({
        theme: 'bootstrap4',
        language: 'es',
        allowClear: true,
        width: '100%',
        ajax: {
            delay: 250,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            url: pathname,
            data: function (params) {
                console.log('[select_customer] Enviando búsqueda:', params.term);
                return {
                    term: params.term,
                    action: 'search_customer'
                };
            },
            processResults: function (data) {
                console.log('[select_customer] Respuesta del servidor:', data);
                console.log('[select_customer] Tipo de data:', typeof data);
                console.log('[select_customer] Es array:', Array.isArray(data));
                if (Array.isArray(data)) {
                    console.log('[select_customer] Cantidad de clientes:', data.length);
                    data.forEach((item, index) => {
                        console.log(`[select_customer] Cliente ${index}:`, item);
                    });
                }
                return {
                    results: data
                };
            },
        },
        placeholder: 'Ingrese un nombre o número de cedula de un cliente',
        minimumInputLength: 1,
    })
        .on('select2:select', function (e) {
            fv.revalidateField('customer');
        })
        .on('select2:clear', function (e) {
            fv.revalidateField('customer');
        });

    $('.btnAddCustomer').on('click', function () {
        var url = $(this).data('url');
        var popupWindow = open_centered_popup(url, 600, 900);
        var checkInterval = setInterval(function () {
            if (popupWindow.closed) {
                clearInterval(checkInterval);
                handle_dynamic_local_storage('customer', select_customer, fv);
            }
        }, 500);
    });

    // Invoice

    input_date_joined.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    input_date_joined.on('change.datetimepicker', function (e) {
        fv.revalidateField('date_joined');
        input_end_credit.datetimepicker('minDate', e.date);
        input_end_credit.datetimepicker('date', e.date);
    });

    input_end_credit.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
        minDate: new moment().format("YYYY-MM-DD")
    });

    input_end_credit.datetimepicker('date', input_end_credit.val());

    input_end_credit.on('change.datetimepicker', function (e) {
        fv.revalidateField('end_credit');
    });

    input_cash
        .TouchSpin({
            min: 0.00,
            max: 100000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10
        })
        .off('change')
        .on('change touchspin.on.min touchspin.on.max', function () {
            fv.revalidateField('cash');
            fv.revalidateField('change');
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    select_payment_type
        .on('change', function () {
            switch (this.value) {
                case "efectivo":
                    invoice.toggleInputVisibility([{'index': 0, 'enable': true}, {'index': 1, 'enable': true}, {'index': 2, 'enable': false}]);
                    fv.enableValidator('cash');
                    fv.enableValidator('change');
                    fv.disableValidator('end_credit');
                    break;
                case "credito":
                    fv.disableValidator('cash');
                    fv.disableValidator('change');
                    fv.enableValidator('end_credit');
                    invoice.toggleInputVisibility([{'index': 0, 'enable': false}, {'index': 1, 'enable': false}, {'index': 2, 'enable': true}]);
                    break;
            }
        });

    select_receipt.on('change', function () {
        execute_ajax_request({
            'params': {
                'action': 'get_receipt_number',
                'receipt': select_receipt.val()
            },
            'success': function (request) {
                $('input[name="receipt_number"]').val(request.receipt_number);
            }
        });
        $('input[name="create_electronic_invoice"]').prop('disabled', $(this).val() !== '01');
        $('input[name="is_draft_invoice"]').prop('disabled', $(this).val() !== '01');
    });

    $('i[data-field="customer"]').hide();
    $('i[data-field="cash"]').hide();
    $('i[data-field="input_search_product"]').hide();

    // Product

    input_search_product.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_product',
                    'term': request.term,
                    'product_id': JSON.stringify(invoice.getProductId()),
                },
                dataType: "json",
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                beforeSend: function () {

                },
                success: function (data) {
                    response(data);
                }
            });
        },
        // Fix: opción correcta es minLength (jQuery UI), no min_length
        minLength: 1,
        delay: 300,
        select: function (event, ui) {
            event.preventDefault();
            $(this).blur();
            if (ui.item.stock === 0 && ui.item.is_inventoried) {
                return message_error('El stock de este producto esta en 0');
            }
            ui.item.quantity = 1;
            invoice.addProduct(ui.item);
            $(this).val('').focus();
        }
    });

    $('.btnClearProducts').on('click', function () {
        input_search_product.val('').focus();
    });

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="quantity"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            invoice.detail.products[tr.row].quantity = parseInt($(this).val());
            invoice.totalCalculator();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + invoice.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('change', 'input[name="current_price"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            invoice.detail.products[tr.row].current_price = parseFloat($(this).val());
            invoice.totalCalculator();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + invoice.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('change', 'input[name="discount"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            invoice.detail.products[tr.row].discount = parseFloat($(this).val());
            invoice.totalCalculator();
            var parent = $(this).closest('.bootstrap-touchspin');
            parent.find('.bootstrap-touchspin-postfix').children().html(invoice.detail.products[tr.row].total_discount.toFixed(2));
            $('td:last', tblProducts.row(tr.row).node()).html('$' + invoice.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            invoice.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            invoice.totalCalculator();
        });

    $('.btnSearchProducts').on('click', function () {
        tblSearchProducts = $('#tblSearchProducts').DataTable({
            autoWidth: false,
            destroy: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'action': 'search_product',
                    'term': input_search_product.val(),
                    'product_id': JSON.stringify(invoice.getProductId()),
                },
                dataSrc: ""
            },
            columns: [
                {data: "code"},
                {data: "short_name"},
                {data: "pvp"},
                {data: "price_promotion"},
                {data: "stock"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-3, -4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(4);
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (row.is_inventoried) {
                            if (row.stock > 0) {
                                return '<span class="badge badge-success badge-pill">' + row.stock + '</span>';
                            }
                            return '<span class="badge badge-danger badge-pill">' + row.stock + '</span>';
                        }
                        return '<span class="badge badge-secondary badge-pill">Sin stock</span>';
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<a rel="add" class="btn btn-success btn-xs btn-flat"><i class="fas fa-plus"></i></a>';
                    }
                }
            ],
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
        $('#myModalSearchProducts').modal('show');
    });

    $('#tblSearchProducts tbody')
        .off()
        .on('click', 'a[rel="add"]', function () {
            var row = tblSearchProducts.row($(this).parents('tr')).data();
            row.quantity = 1;
            invoice.addProduct(row);
            tblSearchProducts.row($(this).parents('tr')).remove().draw();
        });

    $('.btnRemoveAllProducts').on('click', function () {
        if (invoice.detail.products.length === 0) return false;
        dialog_action({
            'content': '¿Estas seguro de eliminar todos los items de tu detalle?',
            'success': function () {
                invoice.detail.products = [];
                invoice.listProducts();
            },
            'cancel': function () {

            }
        });
    });

    // Barcode

    $(document).on('keypress', function (e) {
        if (e.which === 13) {
            e.preventDefault();
            execute_ajax_request({
                'params': {
                    'action': 'search_product_code',
                    'code': input_search_product.val()
                },
                'success': function (request) {
                    input_search_product.autocomplete('close');
                    if (!$.isEmptyObject(request)) {
                        request.quantity = 1;
                        invoice.addProduct(request);
                        input_search_product.val('').focus();
                    } else {
                        message_error('El producto no fue encontrado');
                    }
                }
            });
        }
    });

    // Additional Info

    $('.btnCreateAdditionalInfo').on('click', function () {
        invoice.detail.additional_info.push({'name': '', 'value': ''});
        invoice.listAdditionalInfo();
    });

    $('.btnRemoveAdditionalInfo').on('click', function () {
        if (invoice.detail.additional_info.length === 0) return false;
        dialog_action({
            'content': '¿Estas seguro de eliminar todos los items de tu detalle?',
            'success': function () {
                invoice.detail.additional_info = [];
                invoice.listAdditionalInfo();
            },
            'cancel': function () {

            }
        });
    });

    $('#tblAdditionalInfo tbody')
        .off()
        .on('keyup', 'input[name="additional_info_name"]', function () {
            var tr = tblAdditionalInfo.cell($(this).closest('td, li')).index();
            invoice.detail.additional_info[tr.row].name = $(this).val();
        })
        .on('keyup', 'input[name="additional_info_value"]', function () {
            var tr = tblAdditionalInfo.cell($(this).closest('td, li')).index();
            invoice.detail.additional_info[tr.row].value = $(this).val();
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblAdditionalInfo.cell($(this).closest('td, li')).index();
            invoice.detail.additional_info.splice(tr.row, 1);
            tblAdditionalInfo.row(tr.row).remove().draw();
        });
});