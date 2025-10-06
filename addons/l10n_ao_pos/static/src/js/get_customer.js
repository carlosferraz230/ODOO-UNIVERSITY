odoo.define('l10n_ao_pos.GetCustomer', function(require) {
    "use strict";

    var models = require('point_of_sale.models');

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this, arguments);
            if (this.pos.config.default_partner_id && !this.export_as_JSON().partner_id) {
            	this.set_client(this.pos.db.get_partner_by_id(this.pos.config.default_partner_id[0]));
            }
        },
    });
});