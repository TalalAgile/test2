/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { PlanningSlotPopup } from "@pos_planning/app/components/planning_slot_popup/planning_slot_popup";
import { _t } from "@web/core/l10n/translation";

export class ShiftScreen extends Component {
  static template = "pos_planning.ShiftScreen";
  static props = {};

  setup() {
    this.pos = usePos();
    this.orm = useService("orm");
    this.dialog = useService("dialog");
    const now = new Date();
    const localDate = now.toLocaleDateString("en-CA");

    this.state = useState({
      slots: [],
      workIntervals: {},
      resources: [],
      roles: [],
      partners: [],
      products: [],
      groupedData: {},
      currentDate: localDate,
      startDate: localDate,
      endDate: localDate,
      scale: "day",
      timelineLabels: [],
      isDragging: false,
      dragStart: null,
      dragEnd: null,
      dragResourceId: null,
      dragRowRect: null,
      showScaleDropdown: false,
    });

    onWillStart(async () => {
      this.updateRange();
      await this.loadResources();
      await Promise.all([
        this.loadRoles(),
        this.loadPartners(),
        this.loadProducts(),
        this.loadSlots(),
      ]);
    });
  }

  updateRange() {
    const start = new Date(this.state.currentDate + "T00:00:00");
    if (this.state.scale === "day") {
      this.state.startDate = this.state.currentDate;
      this.state.endDate = this.state.currentDate;
      const labels = [];
      for (let h = 8; h < 21; h++) {
        for (let m = 0; m < 60; m += 15) {
          const hourStr = h < 10 ? "0" + h : h;
          const minStr = m === 0 ? "00" : m;
          labels.push(`${hourStr}:${minStr}`);
        }
      }
      this.state.timelineLabels = labels;
    } else if (this.state.scale === "week") {
      const day = start.getDay();
      const diff = start.getDate() - day + (day === 0 ? -6 : 1);
      start.setDate(diff);
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      this.state.startDate = start.toLocaleDateString("en-CA");
      this.state.endDate = end.toLocaleDateString("en-CA");
      const days = [];
      const d = new Date(this.state.startDate + "T00:00:00");
      for (let i = 0; i < 7; i++) {
        days.push(
          d.toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
        );
        d.setDate(d.getDate() + 1);
      }
      this.state.timelineLabels = days;
    }
  }

  async loadResources() {
    this.state.resources = await this.orm.searchRead(
      "resource.resource",
      [],
      ["name", "color", "role_ids"],
    );
  }
  async loadRoles() {
    this.state.roles = await this.orm.searchRead(
      "planning.role",
      [],
      ["name", "color"],
    );
  }
  async loadPartners() {
    this.state.partners = await this.orm.searchRead(
      "res.partner",
      [],
      ["name", "phone"],
    );
  }
  async loadProducts() {
    this.state.products = await this.orm.searchRead(
      "product.product",
      [["available_in_pos", "=", true]],
      ["display_name", "booking_duration", "lst_price"],
    );
  }

  async loadSlots() {
    try {
      const start = new Date(this.state.startDate + "T00:00:00");
      const end = new Date(this.state.endDate + "T23:59:59");
      const startStr = start.toISOString().replace("T", " ").substring(0, 19);
      const endStr = end.toISOString().replace("T", " ").substring(0, 19);

      const [slots, workIntervals] = await Promise.all([
        this.orm.searchRead(
          "planning.slot",
          [
            ["start_datetime", "<=", endStr],
            ["end_datetime", ">=", startStr],
            ["pos_config_id", "=", this.pos.config.id],
            ["is_available_slot", "=", true],
          ],
          ["start_datetime", "end_datetime", "resource_id", "role_id", "name"],
          { order: "start_datetime asc" },
        ),
        this.orm.call("planning.slot", "get_work_intervals", [], {
          start_datetime: startStr,
          end_datetime: endStr,
          resource_ids: this.state.resources.map((r) => r.id),
        }),
      ]);

      this.state.slots = slots;
      this.state.workIntervals = workIntervals;
      this.groupSlots();
    } catch (error) {
      console.error(error);
      this.state.slots = [];
      this.state.workIntervals = {};
    }
  }

  groupSlots() {
    const grouped = {};
    this.state.resources.forEach((res) => {
      grouped[res.id] = {
        id: res.id,
        name: res.name,
        slots: [],
        work_intervals: [],
      };
    });

    let vStart, vEnd;
    if (this.state.scale === "day") {
      vStart = new Date(this.state.startDate + "T08:00:00");
      vEnd = new Date(this.state.endDate + "T21:00:00");
    } else {
      vStart = new Date(this.state.startDate + "T00:00:00");
      vEnd = new Date(this.state.endDate + "T23:59:59");
    }
    const tRange = vEnd - vStart;

    if (this.state.workIntervals) {
      for (const [resIdStr, intervals] of Object.entries(
        this.state.workIntervals,
      )) {
        const resId = parseInt(resIdStr);
        if (!grouped[resId]) continue;

        intervals.forEach((interval) => {
          const start = new Date(interval.start.replace(" ", "T") + "Z");
          const end = new Date(interval.end.replace(" ", "T") + "Z");
          const offsetMs = Math.max(0, start - vStart);
          const durationMs = Math.min(vEnd, end) - Math.max(vStart, start);
          if (durationMs <= 0) return;

          grouped[resId].work_intervals.push({
            id: `work_${resId}_${interval.start}`,
            style: `left: ${(offsetMs / tRange) * 100}%; width: ${
              (durationMs / tRange) * 100
            }%; position: absolute; top: 5px; bottom: 5px; background-color: rgba(40, 167, 69, 0.15); border: 1px dashed #28a745; z-index: 1; pointer-events: none; border-radius: 4px;`,
          });
        });
      }
    }

    this.state.slots.forEach((slot) => {
      const resId = slot.resource_id ? slot.resource_id[0] : 0;
      if (!grouped[resId]) return;

      const start = new Date(slot.start_datetime.replace(" ", "T") + "Z");
      const end = new Date(slot.end_datetime.replace(" ", "T") + "Z");
      const offsetMs = Math.max(0, start - vStart);
      const durationMs = Math.min(vEnd, end) - Math.max(vStart, start);
      if (durationMs <= 0) return;

      grouped[resId].slots.push({
        ...slot,
        style: `left: ${(offsetMs / tRange) * 100}%; width: ${
          (durationMs / tRange) * 100
        }%; position: absolute; top: 10px; bottom: 10px; background-color: rgba(113, 75, 103, 0.15); border: 1px solid #714B67; border-radius: 6px; z-index: 10; cursor: pointer; display: flex; align-items: center; justify-content: center;`,
      });
    });
    this.state.groupedData = grouped;
  }

  async changeDate(offset) {
    const date = new Date(this.state.currentDate + "T00:00:00");
    if (this.state.scale === "day") date.setDate(date.getDate() + offset);
    else date.setDate(date.getDate() + offset * 7);
    this.state.currentDate = date.toLocaleDateString("en-CA");
    this.updateRange();
    await this.loadSlots();
  }

  async setScale(scale) {
    this.state.scale = scale;
    this.state.showScaleDropdown = false;
    this.updateRange();
    await this.loadSlots();
  }
  toggleScaleDropdown() {
    this.state.showScaleDropdown = !this.state.showScaleDropdown;
  }

  onMouseDown(ev, resId) {
    if (ev.button !== 0) return;
    const rect = ev.currentTarget.getBoundingClientRect();
    let start = (ev.clientX - rect.left) / rect.width;
    if (this.state.scale === "day") start = Math.floor(start * 52) / 52;
    this.state.isDragging = true;
    this.state.dragStart = start;
    this.state.dragEnd = this.state.dragStart;
    this.state.dragResourceId = resId;
    this.state.dragRowRect = rect;
  }

  onMouseMove(ev) {
    if (!this.state.isDragging || !this.state.dragRowRect) return;
    const rect = this.state.dragRowRect;
    let end = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    if (this.state.scale === "day") end = Math.ceil(end * 52) / 52;
    this.state.dragEnd = end;
  }

  async onMouseUp() {
    if (!this.state.isDragging) return;
    const s = Math.min(this.state.dragStart, this.state.dragEnd);
    const e = Math.max(this.state.dragStart, this.state.dragEnd);
    this.state.isDragging = false;
    if (Math.abs(e - s) < 0.001) return;

    let vStart, vEnd;
    if (this.state.scale === "day") {
      vStart = new Date(this.state.startDate + "T08:00:00").getTime();
      vEnd = new Date(this.state.endDate + "T21:00:00").getTime();
    } else {
      vStart = new Date(this.state.startDate + "T00:00:00").getTime();
      vEnd = new Date(this.state.endDate + "T23:59:59").getTime();
    }
    const tRange = vEnd - vStart;

    const startUTC = new Date(vStart + s * tRange)
      .toISOString()
      .replace("T", " ")
      .substring(0, 19);
    const endUTC = new Date(vStart + e * tRange)
      .toISOString()
      .replace("T", " ")
      .substring(0, 19);

    this.openPopup({
      start_datetime: startUTC,
      end_datetime: endUTC,
      resource_id: this.state.dragResourceId,
      is_available_slot: true,
    });
  }

  openPopup(slot, isEdit = false) {
    this.dialog.add(PlanningSlotPopup, {
      title: isEdit ? _t("Edit Shift") : _t("Create Shift"),
      slot: slot,
      resources: this.state.resources,
      roles: this.state.roles,
      partners: this.state.partners,
      products: this.state.products,
      isEdit: isEdit,
      getPayload: async (p) => {
        if (p === null) {
          await this.orm.unlink("planning.slot", [slot.id]);
        } else if (p) {
          const vals = {
            start_datetime: p.start_datetime,
            end_datetime: p.end_datetime,
            resource_id: parseInt(p.resource_id) || false,
            role_id: parseInt(p.role_id) || false,
            name: p.name,
            is_available_slot: true,
            pos_config_id: this.pos.config.id,
          };
          if (isEdit) await this.orm.write("planning.slot", [slot.id], vals);
          else await this.orm.create("planning.slot", [vals]);
        }
        await this.loadSlots();
      },
    });
  }

  async onClickSlot(slot) {
    this.openPopup(slot, true);
  }

  back() {
    this.pos.navigate("PlanningScreen");
  }
}

registry.category("pos_pages").add("ShiftScreen", {
  name: "ShiftScreen",
  component: ShiftScreen,
  route: `/pos/ui/${odoo.pos_config_id}/shifts`,
  params: {},
});
