/** @odoo-module */

import { Component } from "@odoo/owl";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class ShiftsButton extends Component {
    static template = "pos_planning.ShiftsButton";
    setup() {
        this.pos = usePos();
    }
    clickShifts() {
        this.pos.navigate("ShiftScreen");
    }
}

ControlButtons.components.ShiftsButton = ShiftsButton;
