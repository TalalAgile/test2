/** @odoo-module */

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { BookingNotification } from "@pos_planning/app/components/booking_notification/booking_notification";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
  get mainButton() {
    return this.pos.router.state.current === "ActionScreen" &&
      this.pos.router.state.params.actionName === "planning"
      ? "planning"
      : super.mainButton;
  },
});

// Register BookingNotification component so it can be used in the inherited Navbar template
Navbar.components = { ...Navbar.components, BookingNotification };
