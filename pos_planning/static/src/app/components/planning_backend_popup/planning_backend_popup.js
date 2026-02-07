/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class PlanningBackendPopup extends Component {
    static template = "pos_planning.PlanningBackendPopup";
    static components = { Dialog };
    static props = {
        close: Function,
    };

    setup() {
        this.title = _t("Planning Schedule");
        // We use the backend URL for the planning action. 
        // We add 'menu_id' and 'action' to try and get the full view.
        // We also use a hash-based URL which Odoo's web client handles best.
        this.url = `/web#action=planning.planning_action_schedule_by_resource&view_type=gantt`;
    }
}
