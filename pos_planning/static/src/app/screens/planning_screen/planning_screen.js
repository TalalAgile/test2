/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { PlanningSlotPopup } from "@pos_planning/app/components/planning_slot_popup/planning_slot_popup";
import { _t } from "@web/core/l10n/translation";

export class PlanningScreen extends Component {
  static template = "pos_planning.PlanningScreen";
  static props = {};

  setup() {
    this.pos = usePos();
    this.orm = useService("orm");
    this.dialog = useService("dialog");
    this.notification = useService("notification");
    this.busService = useService("bus_service");
    useBus(this.env.bus, "PLANNING_UPDATE", async (payload) => {
      console.log("POS Planning Screen: PLANNING_UPDATE detected! Wait 1s for DB consistency...", payload);

      // Delay to ensure the backend transaction is fully visible via RPC
      setTimeout(async () => {
        try {
          console.log("POS Planning Screen: Reloading slots and intervals...");
          await Promise.all([
            this.loadSlots(),
            this.loadWorkIntervals()
          ]);
          console.log("POS Planning Screen: Gantt refresh sequence completed.");
        } catch (error) {
          console.error("POS Planning Screen: Error during auto-refresh:", error);
        }
      }, 1000);
    });
    const now = new Date();
    const localDate = now.toLocaleDateString("en-CA");

    this.state = useState({
      slots: [],
      resources: [],
      roles: [],
      partners: [],
      products: [],
      groupedData: {},
      currentDate: localDate,
      startDate: localDate,
      endDate: localDate,
      scale: "day",
      hours: Array.from({ length: 24 }, (_, i) => i),
      timelineLabels: [],
      isDragging: false,
      dragStart: null,
      dragEnd: null,
      dragResourceId: null,
      dragRoleId: null,
      dragRowRect: null,
      searchTerm: "",
      showScaleDropdown: false,
      workIntervals: {},
    });

    onWillStart(async () => {
      this.updateRange();
      try {
        await Promise.all([
          this.loadResources(),
          this.loadRoles(),
          this.loadPartners(),
          this.loadProducts(),
          this.loadSlots(),
        ]);
        await this.loadWorkIntervals(); // Load shifts after slots/resources
      } catch (e) {
        console.error(e);
      }
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
      const startOfWeek = new Date(start);
      startOfWeek.setDate(diff);
      this.state.startDate = startOfWeek.toLocaleDateString("en-CA");
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      this.state.endDate = endOfWeek.toLocaleDateString("en-CA");
      const days = [];
      const d = new Date(this.state.startDate + "T00:00:00");
      for (let i = 0; i < 7; i++) {
        days.push(
          d.toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
        );
        d.setDate(d.getDate() + 1);
      }
      this.state.timelineLabels = days;
    } else if (this.state.scale === "month") {
      const startOfMonth = new Date(start.getFullYear(), start.getMonth(), 1);
      this.state.startDate = startOfMonth.toLocaleDateString("en-CA");
      const endOfMonth = new Date(start.getFullYear(), start.getMonth() + 1, 0);
      this.state.endDate = endOfMonth.toLocaleDateString("en-CA");
      const weeks = [];
      const d = new Date(this.state.startDate + "T00:00:00");
      const e = new Date(this.state.endDate + "T23:59:59");
      while (d <= e) {
        weeks.push("W" + this.getWeekNumber(d));
        d.setDate(d.getDate() + 7);
      }
      this.state.timelineLabels = weeks;
    }
  }

  getWeekNumber(d) {
    d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
    var yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
  }

  formatHour(hour) {
    if (hour === 0) return "12am";
    if (hour < 12) return hour + "am";
    if (hour === 12) return "12pm";
    return hour - 12 + "pm";
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

  async loadWorkIntervals() {
    try {
      const startStr = new Date(this.state.startDate + "T00:00:00")
        .toISOString()
        .replace("T", " ")
        .substring(0, 19);
      const endStr = new Date(this.state.endDate + "T23:59:59")
        .toISOString()
        .replace("T", " ")
        .substring(0, 19);
      const intervals = await this.orm.searchRead(
        "planning.slot",
        [
          ["start_datetime", "<=", endStr],
          ["end_datetime", ">=", startStr],
          ["pos_config_id", "=", this.pos.config.id],
          ["is_available_slot", "=", true],
        ],
        ["start_datetime", "end_datetime", "resource_id"],
      );
      this.state.workIntervals = {};
      intervals.forEach((i) => {
        if (!i.resource_id) return;
        const rid = i.resource_id[0];
        if (!this.state.workIntervals[rid]) this.state.workIntervals[rid] = [];
        this.state.workIntervals[rid].push({
          start: new Date(i.start_datetime.replace(" ", "T") + "Z").getTime(),
          end: new Date(i.end_datetime.replace(" ", "T") + "Z").getTime(),
        });
      });
      this.groupSlots(); // Re-group to apply background colors
    } catch (e) {
      console.error(e);
    }
  }

  async loadSlots() {
    try {
      const start = new Date(this.state.startDate + "T00:00:00");
      const end = new Date(this.state.endDate + "T23:59:59");
      const startStr = start.toISOString().replace("T", " ").substring(0, 19);
      const endStr = end.toISOString().replace("T", " ").substring(0, 19);
      const slots = await this.orm.searchRead(
        "planning.slot",
        [
          "|",
          ["pos_config_id", "=", this.pos.config.id],
          ["resource_id.employee_id.pos_config_ids", "in", [this.pos.config.id]],
          ["start_datetime", "<=", endStr],
          ["end_datetime", ">=", startStr],
          ["is_available_slot", "=", false], // Only load actual bookings
        ],
        [
          "start_datetime",
          "end_datetime",
          "resource_id",
          "role_id",
          "name",
          "color",
          "is_available_slot",
          "sale_order_id",
          "booking_line_ids",
          "booking_status",
          "partner_id",
          "phone",
        ],
        { order: "start_datetime asc" },
      );
      console.log(`POS Planning: Loaded ${slots.length} slots from database`);
      this.state.slots = slots;
      this.groupSlots();
    } catch (error) {
      this.state.slots = [];
    }
  }

  groupSlots() {
    const grouped = {};
    const term = (this.state.searchTerm || "").toLowerCase();

    const flatGroup = {
      id: 0,
      name: _t("All Resources"),
      color: 0,
      resources: {},
    };
    grouped[0] = flatGroup;

    this.state.resources.forEach((res) => {
      flatGroup.resources[res.id] = {
        id: res.id,
        name: res.name,
        slots: [],
        overlaps: [],
        unavailable: [],
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

    // Apply work intervals (Gray out non-working times)
    for (const resId in flatGroup.resources) {
      const res = flatGroup.resources[resId];
      const workIntervals = this.state.workIntervals[resId] || [];
      if (workIntervals.length === 0) {
        res.unavailable = [
          { style: "left: 0%; width: 100%; background-color: #f0f0f0;" },
        ];
      } else {
        res.unavailable = [];
        let current = vStart.getTime();
        workIntervals.sort((a, b) => a.start - b.start);
        for (const interval of workIntervals) {
          const start = Math.max(current, interval.start);
          const end = Math.min(vEnd.getTime(), interval.end);
          if (start > current) {
            const offset = Math.max(0, current - vStart.getTime());
            const width = start - current;
            if (width > 0)
              res.unavailable.push({
                style: `left: ${(offset / tRange) * 100}%; width: ${(width / tRange) * 100}%; background-color: #f0f0f0;`,
              });
          }
          current = Math.max(current, end);
        }
        if (current < vEnd.getTime()) {
          const offset = Math.max(0, current - vStart.getTime());
          const width = vEnd.getTime() - current;
          if (width > 0)
            res.unavailable.push({
              style: `left: ${(offset / tRange) * 100}%; width: ${(width / tRange) * 100}%; background-color: #f0f0f0;`,
            });
        }
      }
    }

    this.state.slots.forEach((slot) => {
      const sName = (slot.name || "").toLowerCase();
      const rName = (slot.role_id ? slot.role_id[1] : "").toLowerCase();
      const pName = (slot.partner_id ? slot.partner_id[1] : "").toLowerCase();
      const phone = (slot.phone || "").toLowerCase();
      if (
        term &&
        !(
          sName.includes(term) ||
          rName.includes(term) ||
          pName.includes(term) ||
          phone.includes(term)
        )
      )
        return;

      const resId = slot.resource_id ? slot.resource_id[0] : 0;
      if (!flatGroup.resources[resId]) {
        console.warn(`POS Planning: Skipping slot ${slot.id} - Resource ${resId} not found in Gantt rows`);
        return;
      }

      const start = new Date(slot.start_datetime.replace(" ", "T") + "Z");
      const end = new Date(slot.end_datetime.replace(" ", "T") + "Z");
      const offsetMs = Math.max(0, start - vStart);
      const durationMs = Math.min(vEnd, end) - Math.max(vStart, start);

      flatGroup.resources[resId].slots.push({
        ...slot,
        start,
        end,
        rectStyle: `left: ${(offsetMs / tRange) * 100}%; width: ${(durationMs / tRange) * 100}%;`,
      });
    });

    for (const resId in flatGroup.resources) {
      const res = flatGroup.resources[resId];
      const sorted = [...res.slots].sort((a, b) => a.start - b.start);
      for (let i = 0; i < sorted.length; i++) {
        for (let j = i + 1; j < sorted.length; j++) {
          if (sorted[j].start < sorted[i].end) {
            const ovS = Math.max(sorted[i].start, sorted[j].start);
            const ovE = Math.min(sorted[i].end, sorted[j].end);
            res.overlaps.push({
              style: `left: ${(Math.max(0, ovS - vStart) / tRange) * 100}%; width: ${((ovE - ovS) / tRange) * 100}%;`,
            });
          }
        }
      }
      res.slots.forEach((slot) => {
        let colorCode = "#007BFF";
        let textColor = "#FFFFFF";
        let borderColor = "rgba(255,255,255,0.2)";
        const sN = (slot.name || "").toLowerCase();
        if (sN.includes("closing") || sN.includes("closed"))
          colorCode = "#DC3545";
        else if (slot.booking_status === "ongoing") colorCode = "#28A745";
        else if (slot.booking_status === "finished") colorCode = "#6C757D";
        else if (
          slot.booking_status === "not_started" &&
          slot.booking_line_ids &&
          slot.booking_line_ids.length > 0
        )
          colorCode = "#F7CD1F";
        else if (slot.is_available_slot) colorCode = "#007BFF";
        const isOv = res.overlaps.some(
          (o) =>
            (slot.start >= o.start && slot.start < o.end) ||
            (slot.end > o.start && slot.end <= o.end),
        );
        if (isOv) {
          colorCode = "#FD7E14";
          textColor = "#FFFFFF";
        }
        slot.ganttStyle =
          slot.rectStyle +
          `background-color: ${colorCode}; color: ${textColor}; border: 1px solid ${borderColor}; z-index: ${isOv ? 70 : 10};`;
      });
    }
    this.state.groupedData = grouped;
  }

  getOdooColor(colorIndex) {
    const colors = [
      "#714B67",
      "#F06050",
      "#F4A460",
      "#F7CD1F",
      "#6CC1ED",
      "#814968",
      "#EB7E7F",
      "#2C8397",
      "#475569",
      "#1D4ED8",
    ];
    return colors[colorIndex % colors.length] || "#714B67";
  }

  async changeDate(offset) {
    const date = new Date(this.state.currentDate + "T00:00:00");
    if (this.state.scale === "day") date.setDate(date.getDate() + offset);
    else if (this.state.scale === "week")
      date.setDate(date.getDate() + offset * 7);
    else if (this.state.scale === "month")
      date.setMonth(date.getMonth() + offset);
    this.state.currentDate = date.toLocaleDateString("en-CA");
    this.updateRange();
    await this.loadSlots();
    await this.loadWorkIntervals();
  }

  async setScale(scale) {
    this.state.scale = scale;
    this.state.showScaleDropdown = false;
    this.updateRange();
    await Promise.all([this.loadSlots(), this.loadWorkIntervals()]);
  }

  toggleScaleDropdown() {
    this.state.showScaleDropdown = !this.state.showScaleDropdown;
  }
  async setToday() {
    this.state.currentDate = new Date().toLocaleDateString("en-CA");
    this.updateRange();
    await this.loadSlots();
    await this.loadWorkIntervals();
  }

  onMouseDown(ev, roleId, resId) {
    if (ev.button !== 0) return;

    let vStart, vEnd;
    if (this.state.scale === "day") {
      vStart = new Date(this.state.startDate + "T08:00:00").getTime();
      vEnd = new Date(this.state.endDate + "T21:00:00").getTime();
    } else {
      vStart = new Date(this.state.startDate + "T00:00:00").getTime();
      vEnd = new Date(this.state.endDate + "T23:59:59").getTime();
    }
    const tRange = vEnd - vStart;

    const rect = ev.currentTarget.getBoundingClientRect();
    let start = (ev.clientX - rect.left) / rect.width;
    if (this.state.scale === "day") start = Math.floor(start * 52) / 52;

    const clickTime = vStart + start * tRange;
    const workIntervals = this.state.workIntervals[resId] || [];
    const isAvailable = workIntervals.some(
      (i) => clickTime >= i.start && clickTime < i.end,
    );

    if (!isAvailable) {
      this.notification.add(_t("Cannot book outside of scheduled shifts."), {
        type: "danger",
      });
      return;
    }

    this.state.isDragging = true;
    this.state.dragStart = start;
    this.state.dragEnd = this.state.dragStart;
    this.state.dragResourceId = resId;
    this.state.dragRoleId = roleId;
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
    this.openCreatePopup({
      start_datetime: startUTC,
      end_datetime: endUTC,
      resource_id: this.state.dragResourceId || false,
      role_id: this.state.dragRoleId || false,
    });
  }

  getDragStyle() {
    if (!this.state.isDragging) return "display: none;";
    const l = Math.min(this.state.dragStart, this.state.dragEnd) * 100;
    const w =
      Math.max(0.001, Math.abs(this.state.dragEnd - this.state.dragStart)) *
      100;
    return `left: ${l}%; width: ${w}%; display: block !important;`;
  }

  openCreatePopup(defaultVals) {
    this.dialog.add(PlanningSlotPopup, {
      title: _t("Create Slot"),
      slot: defaultVals,
      resources: this.state.resources,
      roles: this.state.roles,
      partners: this.state.partners,
      products: this.state.products,
      isEdit: false,
      getPayload: async (p) => {
        if (p) {
          const savedPartnerId = await this.createSlotAndOrder(p);
          if (p.copy_partner && savedPartnerId) {
            // Short delay to let UI refresh, then reopen with partner data
            setTimeout(() => {
              this.openCreatePopup({
                start_datetime: this.state.currentDate + " 08:00:00",
                end_datetime: this.state.currentDate + " 17:00:00",
                partner_id: savedPartnerId,
                partnerSearchTerm: p.partnerSearchTerm,
                phone: p.phone,
                resource_id: p.resource_id, // Keep same resource
              });
            }, 200);
          }
        }
      },

    });
  }

  async onClickCreate() {
    this.openCreatePopup({
      start_datetime: this.state.currentDate + " 08:00:00",
      end_datetime: this.state.currentDate + " 17:00:00",
    });
  }

  async onClickSlot(slot) {
    this.dialog.add(PlanningSlotPopup, {
      title: _t("Edit Slot"),
      slot: slot,
      resources: this.state.resources,
      roles: this.state.roles,
      partners: this.state.partners,
      products: this.state.products,
      isEdit: true,
      getPayload: async (p) => {
        if (p === null) {
          await this.orm.unlink("planning.slot", [slot.id]);
          await this.loadSlots();
        } else if (p) {
          const savedPartnerId = await this.updateSlotAndOrder(slot.id, p);
          if (p.copy_partner) {
            // For edit mode, we save then open a NEW slot for the same customer
            setTimeout(() => {
              this.openCreatePopup({
                start_datetime: this.state.currentDate + " 08:00:00",
                end_datetime: this.state.currentDate + " 17:00:00",
                partner_id: savedPartnerId || slot.partner_id[0],
                partnerSearchTerm: p.partnerSearchTerm,
                phone: p.phone,
                resource_id: p.resource_id,
              });
            }, 200);
          }
        }
      },

    });
  }

  async createSlotAndOrder(p) {
    console.log("POS Planning Screen: Creating slot with payload:", p);
    const partnerIdRaw = (p.partner_id || p.partner_id === 0) ? p.partner_id : false;
    let partnerId = partnerIdRaw !== false ? parseInt(partnerIdRaw) : false;
    if (isNaN(partnerId)) partnerId = false;

    if (!partnerId && p.partnerSearchTerm) {
      console.log("POS Planning Screen: Creating new partner:", p.partnerSearchTerm);
      const createdId = await this.orm.create("res.partner", [
        { name: p.partnerSearchTerm, phone: p.phone || "" },
      ]);
      partnerId = Array.isArray(createdId) ? createdId[0] : createdId;
      console.log("POS Planning Screen: New partner created with ID:", partnerId);
      await this.loadPartners();
    }

    // Force is_available_slot = false if we have a partner or services
    const isAvailable = p.is_available_slot && !partnerId && (!p.booking_line_ids || p.booking_line_ids.length === 0);

    console.log("POS Planning Screen: Creating slot with final partnerId:", partnerId);
    await this.orm.create("planning.slot", [
      {
        start_datetime: p.start_datetime.replace("T", " "),
        end_datetime: p.end_datetime.replace("T", " "),
        resource_id: parseInt(p.resource_id) || false,
        role_id: parseInt(p.role_id) || false,
        name: p.name,
        is_available_slot: isAvailable,
        booking_line_ids: [[6, 0, p.booking_line_ids || []]],
        booking_status: p.booking_status,
        partner_id: (partnerId || partnerId === 0) ? partnerId : false,
        phone: p.phone,
        pos_config_id: this.pos.config.id,
      },
    ]);
    await this.loadSlots();
    return partnerId;
  }


  async updateSlotAndOrder(slotId, p) {
    console.log("POS Planning Screen: Updating slot %s with payload:", slotId, p);
    const partnerIdRaw = (p.partner_id || p.partner_id === 0) ? p.partner_id : false;
    let partnerId = partnerIdRaw !== false ? parseInt(partnerIdRaw) : false;
    if (isNaN(partnerId)) partnerId = false;

    if (!partnerId && p.partnerSearchTerm) {
      console.log("POS Planning Screen: Creating new partner (update):", p.partnerSearchTerm);
      const createdId = await this.orm.create("res.partner", [
        { name: p.partnerSearchTerm, phone: p.phone || "" },
      ]);
      partnerId = Array.isArray(createdId) ? createdId[0] : createdId;
      console.log("POS Planning Screen: New partner created with ID:", partnerId);
      await this.loadPartners();
    }

    // Force is_available_slot = false if we have a partner or services
    const isAvailable = p.is_available_slot && !partnerId && (!p.booking_line_ids || p.booking_line_ids.length === 0);

    console.log("POS Planning Screen: Updating slot with final partnerId:", partnerId);
    await this.orm.write("planning.slot", [slotId], {
      start_datetime: p.start_datetime.replace("T", " "),
      end_datetime: p.end_datetime.replace("T", " "),
      resource_id: parseInt(p.resource_id) || false,
      role_id: parseInt(p.role_id) || false,
      name: p.name,
      is_available_slot: isAvailable,
      booking_line_ids: [[6, 0, p.booking_line_ids || []]],
      booking_status: p.booking_status,
      partner_id: (partnerId || partnerId === 0) ? partnerId : false,
      phone: p.phone,
    });
    await this.loadSlots();
    return partnerId;
  }


  back() {
    this.pos.navigate("ProductScreen");
  }
}
