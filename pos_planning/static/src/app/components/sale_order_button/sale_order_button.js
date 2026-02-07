/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
// Import ControlButtons to patch it
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

export class SaleOrderButton extends Component {
  static template = "pos_planning.SaleOrderButton";
  static props = {
    class: { type: String, optional: true },
  };
  setup() {
    this.pos = usePos();
    this.dialog = useService("dialog");
  }
  click() {
    const partner = this.pos.getOrder()?.getPartner();
    const context = {};
    if (partner) {
      context["search_default_partner_id"] = partner.id;
    }

    let domain = [
      ["state", "!=", "cancel"],
      ["invoice_status", "!=", "invoiced"],
      ["currency_id", "=", this.pos.currency.id],
      ["amount_unpaid", ">", 0],
    ];
    if (partner) {
      domain = [
        ...domain,
        ["partner_id", "any", [["id", "child_of", [partner.id]]]],
      ];
    }

    this.dialog.add(SelectCreateDialog, {
      resModel: "sale.order",
      noCreate: true,
      multiSelect: false,
      domain,
      context: context,
      onSelected: async (resIds) => {
        await this.pos.onClickSaleOrder(resIds[0]);
      },
    });
  }
}

// Crucial: Register the component so ControlButtons can find it in its template
ControlButtons.components = { ...ControlButtons.components, SaleOrderButton };
