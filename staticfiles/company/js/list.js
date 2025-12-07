var companyAdmin = {
    list: function () {
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
                data: {
                    'action': 'search'
                },
                dataSrc: ''
            },
            columns: [
                {data: 'id'},
                {data: 'commercial_name'},
                {data: 'company_name'},
                {data: 'ruc'},
                {data: 'owner_name'},
                {data: 'email'},
                {data: 'id'}
            ],
            columnDefs: [
                {
                    targets: [-3],
                    render: function (data, type, row) {
                        if (row.owner_name && row.owner_username) {
                            return row.owner_name + ' (' + row.owner_username + ')';
                        }
                        if (row.owner_name) {
                            return row.owner_name;
                        }
                        if (row.owner_username) {
                            return row.owner_username;
                        }
                        return '';
                    }
                },
                {
                    targets: [-1],
                    className: 'text-center',
                    render: function (data, type, row) {
                        var buttons = '<a href="' + pathname + 'update/' + row.id + '/" data-toggle="tooltip" title="Editar" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                        buttons += '<a href="' + pathname + 'delete/' + row.id + '/" data-toggle="tooltip" title="Eliminar" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a>';
                        return buttons;
                    }
                }
            ],
            initComplete: function (settings, json) {
                $('[data-toggle="tooltip"]').tooltip();
                $(this).wrap("<div class='dataTables_scroll'><div/>");
            }
        });
    }
};

$(function () {
    companyAdmin.list();
});
