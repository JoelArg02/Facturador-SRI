var input_date_range;
var tblQuotation;

var quotation = {
    list: function (args = {}) {
        var params = {'action': 'search'};
        if ($.isEmptyObject(args)) {
            params['start_date'] = input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD');
            params['end_date'] = input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD');
        } else {
            params = Object.assign({}, params, args);
        }
        tblQuotation = $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: params,
                dataSrc: ""
            },
            order: [[0, "desc"], [5, "desc"]],
            columns: [
                {data: "id"},
                {data: "number"},
                {data: "date_joined"},
                {data: "customer.user.names"},
                {data: "subtotal"},
                {data: "total_tax"},
                {data: "total_discount"},
                {data: "total_amount"},
                {data: "id"},
            ],
            select: true,
            columnDefs: [
                {
                    targets: [0],
                    type: 'num',
                    class: 'text-center'
                },
                {
                    targets: [1, 2, 3],
                    class: 'text-center'
                },
                {
                    targets: [-2, -3, -4, -5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(2);
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        var buttons = '<div class="btn-group" role="group">';
                        buttons += '<div class="btn-group" role="group">';
                        buttons += '<button type="button" class="btn btn-secondary btn-sm dropdown-toggle" data-toggle="dropdown" aria-expanded="false"><i class="fas fa-list"></i> Opciones</button>';
                        buttons += '<div class="dropdown-menu dropdown-menu-right">';
                        buttons += '<a class="dropdown-item" rel="detail"><i class="fas fa-folder-open"></i> Detalle de productos</a>';
                        buttons += '<a href="' + pathname + 'update/' + row.id + '/" class="dropdown-item"><i class="fas fa-edit"></i> Editar</a>';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" class="dropdown-item"><i class="fas fa-trash-alt"></i> Eliminar</a>';
                        if (row.validate_stock) {
                            buttons += '<a rel="create_electronic_invoice" class="dropdown-item"><i class="fas fa-file-invoice-dollar"></i> Crear factura electrónica</a>';
                        }
                        buttons += '<a rel="create_draft_invoice" class="dropdown-item"><i class="fas fa-file-invoice"></i> Crear factura borrador</a>';
                        buttons += '<a href="' + pathname + 'print/' + row.id + '/" target="_blank" class="dropdown-item"><i class="fas fa-print"></i> Imprimir</a>';
                        buttons += '<a rel="send_quotation_by_email" class="dropdown-item"><i class="fas fa-envelope"></i> Enviar proforma por email</a>';
                        buttons += '</div></div></div>';
                        return buttons;
                    }
                }
            ],
            initComplete: function (settings, json) {
                // $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="detail"]', function () {
            $('.tooltip').remove();
            var tr = tblQuotation.cell($(this).closest('td, li')).index();
            var row = tblQuotation.row(tr.row).data();
            $('#tblProducts').DataTable({
                autoWidth: false,
                destroy: true,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detail_products',
                        'id': row.id
                    },
                    dataSrc: ""
                },
                columns: [
                    {data: "product.code"},
                    {data: "product.name"},
                    {data: "price"},
                    {data: "stock"},
                    {data: "quantity"},
                    {data: "total_discount"},
                    {data: "total_amount"},
                ],
                columnDefs: [
                    {
                        targets: [-5],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + data.toFixed(4);
                        }
                    },
                    {
                        targets: [-4],
                        class: 'text-center',
                        render: function (data, type, row) {
                            if (row.product.is_inventoried) {
                                return row.product.stock;
                            }
                            return '---';
                        }
                    },
                    {
                        targets: [-3],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return row.quantity + ' ' + (row.validate_stock ? '<span class="badge badge-success badge-pill p-1"><i class="fas fa-check-circle"></i></span>' : '<span class="badge badge-danger badge-pill p-1"><i class="fa-solid fa-circle-minus"></i></span>');
                        }
                    },
                    {
                        targets: [-1, -2],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + data.toFixed(2);
                        }
                    },
                ],
                initComplete: function (settings, json) {
                    $(this).wrap('<div class="dataTables_scroll"><div/>');
                }
            });
            $('#myModalDetail').modal('show');
        })
        .on('click', 'a[rel="create_electronic_invoice"]', function () {
            $('.tooltip').remove();
            var tr = tblQuotation.cell($(this).closest('td, li')).index();
            var row = tblQuotation.row(tr.row).data();
            var params = new FormData();
            params.append('action', 'create_electronic_invoice');
            params.append('id', row.id);
            var args = {
                'params': params,
                'content': '¿Estas seguro de generar la factura electrónica?',
                'success': function (request) {
                    alert_sweetalert({
                        'message': 'Factura generada correctamente',
                        'timer': 2000,
                        'callback': function () {
                            tblQuotation.ajax.reload();
                        }
                    })
                }
            };
            submit_with_formdata(args);
        })
        .on('click', 'a[rel="send_quotation_by_email"]', function () {
            $('.tooltip').remove();
            var tr = tblQuotation.cell($(this).closest('td, li')).index();
            var row = tblQuotation.row(tr.row).data();
            var params = new FormData();
            params.append('action', 'send_quotation_by_email');
            params.append('id', row.id);
            var args = {
                'params': params,
                'content': '¿Estas seguro de enviar la proforma?',
                'success': function (request) {
                    alert_sweetalert({
                        'message': 'Se ha enviado la proforma por email',
                        'timer': 2000,
                        'callback': function () {
                            tblQuotation.ajax.reload();
                        }
                    })
                }
            };
            submit_with_formdata(args);
        })
        .on('click', 'a[rel="create_draft_invoice"]', function () {
            $('.tooltip').remove();
            var tr = tblQuotation.cell($(this).closest('td, li')).index();
            var row = tblQuotation.row(tr.row).data();
            var params = new FormData();
            params.append('action', 'create_draft_invoice');
            params.append('id', row.id);
            var args = {
                'params': params,
                'content': '¿Estas seguro de crear la factura electrónica en borrador?',
                'success': function (request) {
                    alert_sweetalert({
                        'message': 'Se ha creado correctamente la factura electrónica en borrador',
                        'timer': 2000,
                        'callback': function () {
                            tblQuotation.ajax.reload();
                        }
                    })
                }
            };
            submit_with_formdata(args);
        });

    input_date_range
        .daterangepicker({
                language: 'auto',
                startDate: new Date(),
                locale: {
                    format: 'YYYY-MM-DD',
                },
                autoApply: true,
            }
        )
        .on('change.daterangepicker apply.daterangepicker', function (ev, picker) {
            quotation.list();
        });

    $('.drp-buttons').hide();

    quotation.list();

    $('.btnSearchAll').on('click', function () {
        quotation.list({'start_date': '', 'end_date': ''});
    });
});