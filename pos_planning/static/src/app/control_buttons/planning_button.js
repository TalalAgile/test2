/** @odoo-module */

import { Component } from "@odoo/owl";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class PlanningButton extends Component {
    static template = "pos_planning.PlanningButton";
    setup() {
        this.pos = usePos();
    }
    clickPlanning() {
        this.pos.navigate("PlanningScreen");
    }
}

ControlButtons.components.PlanningButton = PlanningButton;
