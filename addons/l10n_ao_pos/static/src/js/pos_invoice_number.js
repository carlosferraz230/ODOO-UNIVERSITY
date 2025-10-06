odoo.define("l10n_ao_pos.OrderReceipt", function (require) {
  "use strict";

  const core = require("web.core");
  const qweb = core.qweb;

  var model = require("point_of_sale.models");
  var SuperPosModel = model.PosModel.prototype;
  var SuperOrder = model.Order.prototype;
  var rpc = require("web.rpc");

  var SuperOrder = model.Order.prototype;
  model.Order = model.Order.extend({
    initialize: function (attributes, options) {
      SuperOrder.initialize.apply(this, arguments);
      this.to_invoice = true;
    },
    init_from_JSON: function (json) {
      var partner_id = 0;
      var res = SuperOrder.init_from_JSON.apply(this, arguments);
      this.to_invoice = true;

      return res
    },
  });

  model.PosModel = model.PosModel.extend({
    _flush_orders: function (orders, options) {
      
      var self = this;
      var result, data;

      result = data = SuperPosModel._flush_orders.call(this, orders, options);
      _.each(orders, function (order) {
        if (order.to_invoice)
          data.then(function (order_server_id) {
            rpc
              .query({
                model: "pos.order",
                method: "read",
                args: [order_server_id, ["account_move"]],
              })
              .then(function (result_dict) {
                if (result_dict.length) {
                  let invoice = result_dict[0].account_move;
                  console.log(result_dict);
                  self.get_order().invoice_number = invoice[1];

                  rpc
                    .query({
                      model: "pos.order",
                      method: "get_hash",
                      context: { invoice_id: invoice[0] },
                    })
                    .then(function (invoice_hash) {
                      self.get_order().hash = invoice_hash;
                    });
                  invoiced.resolve();
                }
              })

              .catch(function (error) {
                return result;
              });
          });
      });
      return result;
    },
  });
  model.Order = model.Order.extend({
    export_for_printing: function () {
      var self = this;
      var receipt = SuperOrder.export_for_printing.call(this);
      if (self.invoice_number) {
        receipt.invoice_number =
          self.invoice_number.split(" ")[0] +
          " " +
          self.invoice_number.split(" ")[1];
        receipt.hash = self.hash;
        // receipt.hash = self.hash.split(" ")[0];
      }
      return receipt;
    },
  });
});
