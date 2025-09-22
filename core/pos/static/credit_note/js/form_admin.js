var fv;
var select_invoice;
var input_search_product, input_date_joined;
var tblProducts;

var credit_note = {
    detail: {
        tax: 0.00,
        products: []
    },
    listProducts: function () {
        this.totalCalculator();
        tblProducts = $('#tblProducts').DataTable({
            autoWidth: false,
            destroy: true,
            data: this.detail.products,
            ordering: false,
            lengthChange: false,
            searching: false,
            paginate: false,
            columns: [
                {data: "id"},
                {data: "product.code"},
                {data: "product.name"},
                {data: "quantity"},
                {data: "new_quantity"},
                {data: "price"},
                {data: "total_discount"},
                {data: "total_amount"},
            ],
            columnDefs: [
                {
                    targets: [0],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<div class="form-check"><label class="form-check-label"><input type="checkbox" name="selected" class="form-control-checkbox" value=""></label></div>';
                    }
                },
                {
                    targets: [-5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data;
                    }
                },
                {
                    targets: [-4],
                    class: 'text-center',
                    width: '20%',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="new_quantity" value="' + row.new_quantity + '">';
                    }
                },
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(4);
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
                }
            ],
            rowCallback: function (row, data, index) {
                var tr = $(row).closest('tr');
                tr.find('input[name="new_quantity"]')
                    .TouchSpin({
                        min: 0,
                        max: data.quantity
                    })
                    .on('keypress', function (e) {
                        return validate_text_box({'event': e, 'type': 'numbers'});
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

                tr.find('input[name="new_quantity"]').prop('disabled', data.selected === 0);
                tr.find('input[name="discount"]').prop('disabled', data.selected === 0);
            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    },
    totalCalculator: function () {
        var tax = this.detail.tax / 100;
        var products = this.detail.products.filter(value => value.selected === 1);
        products.forEach(function (value, index, array) {
            value.tax = parseFloat(tax);
            value.price_with_tax = value.price + (value.price * value.tax);
            value.subtotal = value.price * value.new_quantity;
            value.total_discount = value.subtotal * parseFloat((value.discount / 100));
            value.total_tax = (value.subtotal - value.total_discount) * value.tax;
            value.total_amount = value.subtotal - value.total_discount;
        });
        this.detail.subtotal_without_tax = products.filter(value => !value.product.has_tax).reduce((a, b) => a + (b.total_amount || 0), 0);
        this.detail.subtotal_with_tax = products.filter(value => value.product.has_tax).reduce((a, b) => a + (b.total_amount || 0), 0);
        this.detail.total_discount = products.reduce((a, b) => a + (b.total_discount || 0), 0);
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
};

document.addEventListener('DOMContentLoaded', function (e) {
    fv = FormValidation.formValidation(document.getElementById('frmForm'), {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                invoice: {
                    validators: {
                        notEmpty: {
                            message: 'Seleccione una factura'
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
                receipt_number: {
                    validators: {
                        notEmpty: {}
                    }
                },
                motive: {
                    validators: {
                        notEmpty: {}
                    }
                }
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
            if (credit_note.detail.products.filter(value => value.selected === 1).length === 0) {
                message_error('Debe tener al menos un item activo en el detalle de la nota de credito');
                return false;
            }
            var params = new FormData(fv.form);
            params.append('products', JSON.stringify(credit_note.detail.products));
            var args = {
                'params': params,
                'form': fv.form
            };
            submit_with_formdata(args);
        });
});

$(function () {
    input_date_joined = $('input[name="date_joined"]');
    select_invoice = $('select[name="invoice"]');
    input_search_product = $('input[name="search"]');

    // Invoice

    $('input[name="select_all"]').on('change', function () {
        var checked = this.checked;
        if (tblProducts) {
            var cells = tblProducts.cells().nodes();
            $(cells).find('input[name="selected"]').prop('checked', checked).trigger('change');
        }
    });

    select_invoice.select2({
        theme: 'bootstrap4',
        language: 'es',
        allowClear: true,
        ajax: {
            delay: 250,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            url: pathname,
            data: function (params) {
                return {
                    term: params.term,
                    action: 'search_invoice'
                };
            },
            processResults: function (data) {
                return {
                    results: data
                };
            },
        },
        placeholder: 'Ingrese un número de factura o nombre de un cliente',
        minimumInputLength: 1,
    })
        .on('select2:select', function (e) {
            var invoice = e.params.data;
            credit_note.detail.products = invoice.detail;
            credit_note.listProducts();
            input_date_joined.datetimepicker('minDate', invoice.end_credit);
            input_date_joined.datetimepicker('date', invoice.end_credit);
            $('input[name="select_all"]').prop('checked', 'checked').trigger('change');
            fv.revalidateField('invoice');
        })
        .on('select2:clear', function (e) {
            fv.revalidateField('invoice');
            credit_note.detail.products = [];
            credit_note.listProducts();
            $('input[name="select_all"]').prop('checked', '');
        });

    // credit_note

    input_date_joined.datetimepicker({
        useCurrent: false,
        format: 'YYYY-MM-DD',
        locale: 'es',
        keepOpen: false,
    });

    input_date_joined.on('change.datetimepicker', function (e) {
        fv.revalidateField('date_joined');
    });

    // Product

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="selected"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            credit_note.detail.products[tr.row].selected = this.checked ? 1 : 0;
            $('td', tblProducts.row(tr.row).node()).find('input[type="text"]').prop('disabled', !this.checked);
            credit_note.totalCalculator();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + credit_note.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('change', 'input[name="new_quantity"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            credit_note.detail.products[tr.row].new_quantity = parseInt($(this).val());
            credit_note.totalCalculator();
            $('td:last', tblProducts.row(tr.row).node()).html('$' + credit_note.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('change', 'input[name="discount"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            credit_note.detail.products[tr.row].discount = parseFloat($(this).val());
            credit_note.totalCalculator();
            $(this).next().find('.input-group-text').html(credit_note.detail.products[tr.row].total_discount.toFixed(2));
            $('td:last', tblProducts.row(tr.row).node()).html('$' + credit_note.detail.products[tr.row].total_amount.toFixed(2));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            credit_note.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            tblProducts.clear().rows.add(credit_note.detail.products).draw();
            credit_note.totalCalculator();
        });
});