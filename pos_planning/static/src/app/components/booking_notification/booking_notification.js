/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class BookingNotification extends Component {
  static template = "pos_planning.BookingNotification";
  static props = {};

  setup() {
    this.pos = usePos();
    this.busService = useService("bus_service");
    // Listens to global bus bridged by pos_store
    this.state = useState({
      count: 0,
    });

    useBus(this.env.bus, "PLANNING_UPDATE", () => {
      this.state.count++;
    });
  }

  /**
   * Resets the booking counter and triggers the Planning view navigation.
   */
  async resetCount() {
    this.state.count = 0;
    try {
      await this.pos.openPlanning();
    } catch (error) {
      console.error("Error navigating to Planning from notification:", error);
    }
  }
}
