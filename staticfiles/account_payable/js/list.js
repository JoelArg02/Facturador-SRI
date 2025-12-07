var tblAccountsPayableDetail, tblAccountsPayable;
var input_date_range;
var account_payable = {
    list: function (args = {}) {
        var params = {'action': 'search'};
        if ($.isEmptyObject(args)) {
            params['start_date'] = input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD');
            params['end_date'] = input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD');
        } else {
            params = Object.assign({}, params, args);
        }
        tblAccountsPayable = $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: params,
                dataSrc: ""
            },
            columns: [
                {data: "purchase.number"},
                {data: "purchase.provider.name"},
                {data: "date_joined"},
                {data: "end_date"},
                {data: "debt"},
                {data: "balance"},
                {data: "active"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-5, -6],
                    class: 'text-center',
                },
                {
                    targets: [-3, -4],
                    orderable: false,
                    class: 'text-center',
                    render: function (data, type, row) {
                        return '$' + data.toFixed(2);
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        if (data) {
                            return '<span class="badge badge-danger badge-pill">Adeuda</span>';
                        }
                        return '<span class="badge badge-success badge-pill">Pagado</span>';
                    }
                },
                {
                    targets: [-1],
                    orderable: false,
                    class: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a rel="payments" data-toggle="tooltip" title="Pagos" class="btn bg-blue btn-xs btn-flat"><i class="fas fa-dollar-sign"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a>';
                        return buttons;
                    }
                },
            ],
            initComplete: function (settings, json) {
                $('[data-toggle="tooltip"]').tooltip();
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');

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
            account_payable.list();
        });

    $('.drp-buttons').hide();

    account_payable.list();

    $('.btnSearchAll').on('click', function () {
        account_payable.list({'start_date': '', 'end_date': ''});
    });

    $('#data tbody')
        .off()
        .on('click', 'a[rel="payments"]', function () {
            $('.tooltip').remove();
            var tr = tblAccountsPayable.cell($(this).closest('td, li')).index(),
                row = tblAccountsPayable.row(tr.row).data();
            tblAccountsPayableDetail = $('#tblPayments').DataTable({
                autoWidth: false,
                destroy: true,
                searching: false,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: function (d) {
                        d.action = 'search_payments';
                        d.id = row.id;
                    },
                    dataSrc: ""
                },
                columns: [
                    {data: "index"},
                    {data: "date_joined"},
                    {data: "amount"},
                    {data: "description"},
                    {data: "amount"},
                ],
                columnDefs: [
                    {
                        targets: [-3],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '$' + data.toFixed(2);
                        }
                    },
                    {
                        targets: [-1],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return '<a rel="delete" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-times"></i></a>';
                        }
                    }
                ],
                rowCallback: function (row, data, index) {

                },
                initComplete: function (settings, json) {
                    $(this).wrap('<div class="dataTables_scroll"><div/>');
                }
            });
            $('#myModalPayments').modal('show');
        });

    $('#tblPayments tbody')
        .off()
        .on('click', 'a[rel="delete"]', function () {
            $('.tooltip').remove();
            var tr = tblAccountsPayableDetail.cell($(this).closest('td, li')).index(),
                row = tblAccountsPayableDetail.row(tr.row).data();
            var params = new FormData();
            params.append('id', row.id);
            params.append('action', 'delete_payment');
            var args = {
                'params': params,
                'content': '¿Estas seguro de eliminar el registro?',
                'success': function (request) {
                    tblAccountsPayableDetail.ajax.reload();
                }
            };
            submit_with_formdata(args);
        });

    $('#myModalPayments').on('hidden.bs.modal', function () {
        tblAccountsPayable.ajax.reload();
    });
});
