odoo.define('fleetprd.fleet_cost_dashboard_pdf', function (require) {
    "use strict";

    var DashboardController = require('web_dashboard.DashboardController');

    DashboardController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);

            if (this.modelName !== 'fleet.cost.analysis') {
                return;
            }

            if (!this.$buttons) {
                this.$buttons = $('<div/>');
            }

            if (!this.$buttons.find('.o_fleet_dashboard_pdf').length) {
                $('<button/>', {
                    type: 'button',
                    class: 'btn btn-primary o_fleet_dashboard_pdf',
                    html: '<i class="fa fa-file-pdf-o mr-1"/> Baixar PDF',
                })
                    .on('click', this._onPrintFleetDashboardPdf.bind(this))
                    .prependTo(this.$buttons);
            }

            if ($node) {
                this.$buttons.appendTo($node);
            }
        },

        _onPrintFleetDashboardPdf: function () {
            return this._rpc({
                model: 'fleet.cost.analysis',
                method: 'action_print_dashboard_pdf',
                args: [[]],
                context: {
                    active_model: 'fleet.cost.analysis',
                    active_domain: this.actionDomain || [],
                },
            }).then(this.do_action.bind(this));
        },
    });
});
