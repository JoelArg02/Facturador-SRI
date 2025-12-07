var input_date_range;
var tblInvoice;

var invoice = {
    list: function (args = {}) {
        var params = {'action': 'search'};
        if ($.isEmptyObject(args)) {
            params['start_date'] = input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD');
            params['end_date'] = input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD');
        } else {
            params = Object.assign({}, params, args);
        }
        tblInvoice = $('#data').DataTable({
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
                {data: "receipt_number_full"},
                {data: "date_joined"},
                {data: "customer.user.names"},
                {data: "receipt.name"},
                {data: "status.name"},
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
                    targets: [1, -9],
                    class: 'text-center'
                },
                {
                    targets: [-7],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data.toUpperCase();
                    }
                },
                {
                    targets: [-6],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var name = row.status.name;
                        if (row.receipt.voucher_type.id === '08') {
                            return '<span class="badge rounded-pill bg-secondary">Sin facturación</span>';
                        }
                        switch (row.status.id) {
                            case "without_authorizing":
                                return '<span class="badge rounded-pill bg-warning">' + name + '</span>';
                            case "authorized":
                            case "authorized_and_sent_by_email":
                                return '<span class="badge rounded-pill bg-success">' + name + '</span>';
                            case "sequential_registered_error":
                            case "canceled":
                                return '<span class="badge rounded-pill bg-danger">' + name + '</span>';
                        }
                    }
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
                        buttons += '<a target="_blank" href="' + row.print_ticket + '" class="dropdown-item"><i class="fas fa-ticket-alt"></i> Imprimir factura ticket</a> ';
                        if (row.status.id === 'without_authorizing' && row.receipt.voucher_type.id === '01') {
                            buttons += '<a href="' + pathname + 'update/' + row.id + '/" class="dropdown-item"><i class="fas fa-edit"></i> Editar factura electrónica</a>';
                            buttons += '<a rel="create_electronic_invoice" class="dropdown-item"><i class="fas fa-clipboard-check"></i> Generar factura electrónica</a>';
                        } else if (['authorized', 'authorized_and_sent_by_email'].includes(row.status.id)) {
                            buttons += '<a rel="send_receipt_by_email" class="dropdown-item"><i class="fas fa-envelope"></i> Enviar comprobantes por email</a>';
                            buttons += '<a href="' + row.print_pdf + '" target="_blank" class="dropdown-item"><i class="fa-solid fa-file-pdf"></i> Imprimir pdf</a>';
                            buttons += '<a href="' + row.authorized_xml + '" target="_blank" class="dropdown-item"><i class="fas fa-file-code"></i> Descargar xml</a>';
                            if (row.customer.identification_type.id !== '07' && row.receipt.voucher_type.id === '01') {
                                buttons += '<a rel="create_credit_note" class="dropdown-item"><i class="fas fa-minus-circle"></i> Crear nota de credito</a>';
                            }
                        }
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
            var tr = tblInvoice.cell($(this).closest('td, li')).index();
            var row = tblInvoice.row(tr.row).data();
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
                    {data: "quantity"},
                    {data: "total_discount"},
                    {data: "total_amount"},
                ],
                columnDefs: [
                    {
                        targets: [-4],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + data.toFixed(4);
                        }
                    },
                    {
                        targets: [-3],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return data;
                        }
                    },
                    {
                        targets: [-1, -2],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + data.toFixed(2);
                        }
                    }
                ],
                initComplete: function (settings, json) {
                    $(this).wrap('<div class="dataTables_scroll"><div/>');
                }
            });
            $('#myModalDetail').modal('show');
        })
        .on('click', 'a[rel="create_electronic_invoice"]', function () {
            $('.tooltip').remove();
            var tr = tblInvoice.cell($(this).closest('td, li')).index();
            var row = tblInvoice.row(tr.row).data();
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
                            tblInvoice.ajax.reload();
                        }
                    })
                }
            };
            submit_with_formdata(args);
        })
        .on('click', 'a[rel="send_receipt_by_email"]', function () {
            $('.tooltip').remove();
            var tr = tblInvoice.cell($(this).closest('td, li')).index();
            var row = tblInvoice.row(tr.row).data();
            var params = new FormData();
            params.append('action', 'send_receipt_by_email');
            params.append('id', row.id);
            var args = {
                'params': params,
                'content': '¿Estas seguro de enviar la factura pdf/xml por email?',
                'success': function (request) {
                    alert_sweetalert({
                        'message': 'Se ha enviado la factura pdf/xml por email',
                        'timer': 2000,
                        'callback': function () {
                            tblInvoice.ajax.reload();
                        }
                    })
                }
            };
            submit_with_formdata(args);
        })
        .on('click', 'a[rel="create_credit_note"]', function () {
            $('.tooltip').remove();
            var tr = tblInvoice.cell($(this).closest('td, li')).index();
            var row = tblInvoice.row(tr.row).data();
            var params = new FormData();
            params.append('action', 'create_credit_note');
            params.append('id', row.id);
            var args = {
                'params': params,
                'content': '¿Estas seguro de generar la nota de credito?',
                'success': function (request) {
                    alert_sweetalert({
                        'message': 'Se ha generado correctamente la nota de credito',
                        'timer': 2000,
                        'callback': function () {
                            tblInvoice.ajax.reload();
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
            invoice.list();
        });

    $('.drp-buttons').hide();

    invoice.list();

    $('.btnSearchAll').on('click', function () {
        invoice.list({'start_date': '', 'end_date': ''});
    });
});