/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
  async setup() {
    await super.setup(...arguments);
    this.processedMessages = new Set();

    // Method to handle planning updates with de-duplication
    const handleUpdate = (payload) => {
      // Use both payload.id (for new messages) and payload.slots (as fallback if id is somehow missing)
      const msgId = payload && payload.id;
      if (!msgId) {
        console.warn("POS Store: Received PLANNING_UPDATE without ID, forcing reload...");
        this.env.bus.trigger("PLANNING_UPDATE", payload);
        return;
      }

      if (this.processedMessages.has(msgId)) {
        console.log("POS Store: Ignoring duplicate PLANNING_UPDATE", msgId);
        return;
      }
      this.processedMessages.add(msgId);

      // Keep only last 100 messages to prevent memory leak
      if (this.processedMessages.size > 100) {
        const first = this.processedMessages.values().next().value;
        this.processedMessages.delete(first);
      }

      console.log("POS Store: PROCESSING PLANNING_UPDATE", payload);
      this.notification.add(_t("Planning information updated!"), {
        type: "success",
        sticky: false,
      });
      this.env.bus.trigger("PLANNING_UPDATE", payload);
    };

    // 1. CHANNEL A: Native WebSocket (Standard POS)
    console.log("POS Store: Listening to Channel A (Native WebSocket)...");
    this.data.connectWebSocket("PLANNING_UPDATE", (payload) => handleUpdate(payload));

    // 2. CHANNEL B: Global Bus (Fallback)
    console.log("POS Store: Listening to Channel B (Global Fallback)...");
    this.bus.addChannel("pos_planning_global");
    this.bus.addEventListener("notification", ({ detail: notifications }) => {
      for (const { type, payload } of notifications) {
        if (type === "PLANNING_UPDATE") {
          console.log("POS Store: Received PLANNING_UPDATE via Global Fallback");
          handleUpdate(payload);
        }
      }
    });
  },
  async openPlanning() {
    this.navigate("ActionScreen", { actionName: "planning" });
    const action = await this.data.call(
      "planning.slot",
      "action_open_planning_gantt_view",
      [[]],
      { context: { pos_config_id: this.config.id } },
    );
    await this.action.doAction(action);
  },
});