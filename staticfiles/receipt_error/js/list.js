var input_date_range;
var select_receipt;
var receipt_error = {
    list: function () {
        var params = {
            'action': 'search',
            'start_date': input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD'),
            'end_date': input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD'),
            'receipt': select_receipt.val()
        }
        $('#data').DataTable({
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
            order: [[1, "desc"]],
            columns: [
                {data: "time_joined"},
                {data: "receipt_number_full"},
                {data: "receipt.voucher_type.name"},
                {data: "stage.name"},
                {data: "environment_type.name"},
                {
                    data: null,
                    defaultContent: '<pre></pre>',
                    createdCell: function (td, data, row) {
                        $(td).find('pre').jsonViewer(row.errors, {collapsed: true, withQuotes: true, withLinks: false});
                    }
                },
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [-1],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<a href="' + pathname + 'delete/' + row.id + '/" data-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    }
                }
            ],
            initComplete: function (settings, json) {
                $('[data-toggle="tooltip"]').tooltip();
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    }
};

$(function () {
    select_receipt = $('select[name="receipt"]');
    input_date_range = $('input[name="date_range"]');

    $('.select2').select2({
        theme: 'bootstrap4',
        language: 'es'
    });

    select_receipt.on('change', function () {
        receipt_error.list(false);
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
            receipt_error.list();
        });

    $('.drp-buttons').hide();

    receipt_error.list();
});