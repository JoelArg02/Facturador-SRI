var fv;
var tblProducts, tblSearchProducts;
var input_discount_massive, input_date_range, input_search_product;

var promotion = {
    detail: {
        products: [],
    },
    addProduct: function (item) {
        this.detail.products.push(item);
        this.listProducts();
    },
    calculateDiscount: function () {
        const multiplier = 100;
        this.detail.products.forEach(function (value, index, array) {
            value.total_discount = value.pvp * (value.discount / 100);
            value.total_discount = Math.floor(value.total_discount * multiplier) / multiplier;
            value.final_price = value.pvp - value.total_discount;
        });
    },
    listProducts: function () {
        this.calculateDiscount();
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
                {data: "code"},
                {data: "full_name"},
                {data: "pvp"},
                {data: "discount"},
                {data: "total_discount"},
                {data: "final_price"},
            ],
            columnDefs: [
                {
                    targets: [-3],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '<input type="text" class="form-control" autocomplete="off" name="discount" value="' + row.discount + '">';
                    }
                },
                {
                    targets: [-1, -2, -4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(4);
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
                tr.find('input[name="discount"]')
                    .TouchSpin({
                        min: 0.01,
                        max: 100,
                        step: 0.01,
                        decimals: 2,
                        boostat: 5,
                        prefix: '%',
                        maxboostedstep: 10
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
    getProductId: function () {
        return this.detail.products.map(value => value.id);
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
                date_range: {
                    validators: {
                        notEmpty: {},
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
            if (promotion.detail.products.length === 0) {
                return message_error('Debe tener al menos un item en el detalle');
            }
            var params = new FormData(fv.form);
            params.append('products', JSON.stringify(promotion.detail.products));
            params.append('start_date', input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'));
            params.append('end_date', input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'));
            var args = {
                'params': params,
                'form': fv.form
            };
            submit_with_formdata(args);
        });
});

$(function () {
    input_search_product = $('input[name="search_product"]');
    input_discount_massive = $('input[name="discount_massive"]');
    input_date_range = $('input[name="date_range"]');

    input_date_range
        .daterangepicker({
            language: 'auto',
            locale: {
                format: 'YYYY-MM-DD',
            },
        })
        .on('hide.daterangepicker', function (ev, picker) {
            fv.revalidateField('date_range');
        });

    $('.drp-buttons').hide();

    // Products

    input_search_product.autocomplete({
        source: function (request, response) {
            $.ajax({
                url: pathname,
                data: {
                    'action': 'search_product',
                    'term': request.term,
                    'product_id': JSON.stringify(promotion.getProductId()),
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
        min_length: 3,
        delay: 300,
        select: function (event, ui) {
            event.preventDefault();
            $(this).blur();
            ui.item.discount = 0.00;
            promotion.addProduct(ui.item);
            $(this).val('').focus();
        }
    });

    $('.btnClearProducts').on('click', function () {
        input_search_product.val('').focus();
    });

    $('#tblProducts tbody')
        .off()
        .on('change', 'input[name="discount"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            promotion.detail.products[tr.row].discount = parseFloat($(this).val());
            promotion.calculateDiscount();
            $('td:eq(-2)', tblProducts.row(tr.row).node()).html('$' + promotion.detail.products[tr.row].total_discount.toFixed(4));
            $('td:eq(-1)', tblProducts.row(tr.row).node()).html('$' + promotion.detail.products[tr.row].final_price.toFixed(4));
        })
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblProducts.cell($(this).closest('td, li')).index();
            promotion.detail.products.splice(tr.row, 1);
            tblProducts.row(tr.row).remove().draw();
            $('.tooltip').remove();
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
                    'product_id': JSON.stringify(promotion.getProductId()),
                },
                dataSrc: ""
            },
            columns: [
                {data: "code"},
                {data: "full_name"},
                {data: "pvp"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(4);
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var content = '<div class="checkbox">';
                        content += '<label><input type="checkbox" class="form-control-checkbox" name="selected" value=""></label>';
                        content += '</div>';
                        return content;
                    }
                }
            ],
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
        $('input[name="select_all"]').prop('checked', false);
        $('#myModalSearchProducts').modal('show');
    });

    $('#myModalSearchProducts').on('hide.bs.modal', function () {
        var products = tblSearchProducts.rows().data().toArray().filter(function (item, key) {
            return item.selected;
        });
        var discount_massive = parseFloat(input_discount_massive.val());
        products.forEach(function (value, index, array) {
            value.discount = discount_massive;
            promotion.detail.products.push(value);
        });
        promotion.listProducts();
    })

    $('#tblSearchProducts tbody')
        .off()
        .on('click', 'a[rel="add"]', function () {
            var row = tblSearchProducts.row($(this).parents('tr')).data();
            row.discount = 0.01;
            promotion.addProduct(row);
            tblSearchProducts.row($(this).parents('tr')).remove().draw();
        })
        .on('change', 'input[name="selected"]', function () {
            var row = tblSearchProducts.row($(this).parents('tr')).data();
            row.selected = this.checked;
        });

    $('.btnRemoveAllProducts').on('click', function () {
        if (promotion.detail.products.length === 0) return false;
        dialog_action({
            'content': '¿Estas seguro de eliminar todos los items de tu detalle?',
            'success': function () {
                promotion.detail.products = [];
                promotion.listProducts();
            },
            'cancel': function () {

            }
        });
    });

    input_discount_massive
        .TouchSpin({
            min: 0.01,
            max: 1000000,
            step: 0.01,
            decimals: 2,
            boostat: 5,
            maxboostedstep: 10,
            prefix: '%'
        })
        .on('change touchspin.on.min touchspin.on.max', function () {
            var discount_massive = parseFloat($(this).val());
            promotion.detail.products = [];
            tblProducts.rows().data().toArray().forEach(function (value, index, array) {
                value.discount = discount_massive;
                promotion.detail.products.push(value);
            });
            promotion.listProducts();
        })
        .on('keypress', function (e) {
            return validate_text_box({'event': e, 'type': 'decimals'});
        });

    $('input[name="select_all"]')
        .on('change', function () {
            var checked = this.checked;
            var cells = tblSearchProducts.cells().nodes();
            $(cells).find('input[name="selected"]').prop('checked', checked).change();
            tblSearchProducts.rows().data().toArray().forEach(function (value, index, array) {
                value.selected = checked;
            });
        });

    $('i[data-field="input_search_product"]').hide();
    $('i[data-field="discount_massive"]').hide();
});
