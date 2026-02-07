/** @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class PlanningSlotPopup extends Component {
  static template = "pos_planning.PlanningSlotPopup";
  static components = { Dialog };
  static props = {
    title: String,
    slot: Object,
    resources: Array,
    roles: Array,
    partners: Array,
    products: Array,
    isEdit: Boolean,
    getPayload: Function,
    close: Function,
  };
  static defaultProps = { isEdit: false };

  setup() {
    const startUTC = this.props.slot.start_datetime || "";
    const endUTC = this.props.slot.end_datetime || "";

    let initialSids = [];
    if (this.props.slot.booking_line_ids) {
      const raw = this.props.slot.booking_line_ids;
      if (Array.isArray(raw)) {
        if (Array.isArray(raw[0])) initialSids = raw[0][2] || [];
        else initialSids = raw;
      }
    }

    this.state = useState({
      start_datetime: this.utcToLocalInput(startUTC),
      end_datetime: this.utcToLocalInput(endUTC),
      resource_id: this.props.slot.resource_id
        ? Array.isArray(this.props.slot.resource_id)
          ? this.props.slot.resource_id[0]
          : this.props.slot.resource_id
        : "",
      role_id: this.props.slot.role_id
        ? Array.isArray(this.props.slot.role_id)
          ? this.props.slot.role_id[0]
          : this.props.slot.role_id
        : "",
      name: this.props.slot.name || "",
      is_available_slot: this.props.slot.is_available_slot || false,
      booking_line_ids: initialSids,
      booking_status: this.props.slot.booking_status || "not_started",
      partner_id: this.props.slot.partner_id
        ? Array.isArray(this.props.slot.partner_id)
          ? this.props.slot.partner_id[0]
          : this.props.slot.partner_id
        : false,
      phone: this.props.slot.phone || "",
      showDeleteConfirm: false,
      partnerSearchTerm: this.props.slot.partner_id
        ? Array.isArray(this.props.slot.partner_id)
          ? this.props.slot.partner_id[1]
          : ""
        : "",
      showPartnerList: false,
      productSearchTerm: "",
    });
  }

  get filteredPartners() {
    const term = (this.state.partnerSearchTerm || "").toLowerCase();
    if (!term) return this.props.partners.slice(0, 20);
    return this.props.partners
      .filter(
        (p) =>
          (p.name || "").toLowerCase().includes(term) ||
          (p.phone || "").toLowerCase().includes(term),
      )
      .slice(0, 20);
  }

  get filteredProducts() {
    const term = (this.state.productSearchTerm || "").toLowerCase();
    if (!term) return this.props.products.slice(0, 10);
    return this.props.products
      .filter((p) => (p.display_name || "").toLowerCase().includes(term))
      .slice(0, 10);
  }

  utcToLocalInput(utcStr) {
    if (!utcStr) return "";
    const date = new Date(utcStr.replace(" ", "T") + "Z");
    if (isNaN(date.getTime())) return "";
    const offset = date.getTimezoneOffset() * 60000;
    const local = new Date(date.getTime() - offset);
    return local.toISOString().substring(0, 16);
  }

  localInputToUTC(localStr) {
    if (!localStr) return "";
    const date = new Date(localStr);
    return date.toISOString().replace("T", " ").substring(0, 19);
  }

  onStartChange(ev) {
    const newStart = ev.target.value;
    this.state.start_datetime = newStart;
    if (
      newStart &&
      (!this.state.end_datetime || this.state.end_datetime <= newStart)
    ) {
      const date = new Date(newStart);
      date.setMinutes(date.getMinutes() + 15);
      const offset = date.getTimezoneOffset() * 60000;
      const local = new Date(date.getTime() - offset);
      this.state.end_datetime = local.toISOString().substring(0, 16);
    }
  }

  onPhoneInput(ev) {
    const val = ev.target.value;
    this.state.phone = val;
    // Search by phone: Autofill Customer
    if (val.length >= 3) {
      const match = this.props.partners.find(
        (p) => p.phone && p.phone.includes(val),
      );
      if (match) {
        this.state.partner_id = match.id;
        this.state.partnerSearchTerm = match.name;
      }
    }
  }

  onPartnerSearchInput(ev) {
    const val = ev.target.value;
    this.state.partnerSearchTerm = val;
    this.state.partner_id = false;
    this.state.showPartnerList = val && val.length > 0;
    console.log("POS Planning Popup: Partner search input:", val);
  }

  onPartnerSearchKeyDown(ev) {
    if (ev.key === "Enter" && this.state.showPartnerList) {
      const match = this.filteredPartners[0];
      if (match) {
        this.selectPartner(match);
        ev.preventDefault();
      }
    }
  }

  onPartnerChange(ev) {
    const val = ev.target.value;
    const partnerId = val ? parseInt(val) : false;
    this.state.partner_id = partnerId;
    const partner = this.props.partners.find((p) => p.id === partnerId);
    if (partner) {
      this.state.phone = partner.phone || "";
      this.state.partnerSearchTerm = partner.name;
    }
  }

  // NEW: Autocomplete selection for services
  selectProduct(p) {
    if (p && !this.state.booking_line_ids.includes(p.id)) {
      this.state.booking_line_ids.push(p.id);
      // Autofill Task Name if default or empty
      if (!this.state.name || this.state.name === "Morning Shift") {
        this.state.name = p.display_name;
      }
      // Auto duration (minimum 15 minutes)
      if (
        !this.props.isEdit &&
        (!this.state.end_datetime ||
          this.state.end_datetime === this.state.start_datetime)
      ) {
        const duration = Math.max(p.booking_duration || 0, 15);
        const date = new Date(this.state.start_datetime);
        date.setMinutes(date.getMinutes() + duration);
        const offset = date.getTimezoneOffset() * 60000;
        const local = new Date(date.getTime() - offset);
        this.state.end_datetime = local.toISOString().substring(0, 16);
      }
    }
    this.state.productSearchTerm = "";
  }

  onProductSearchKeydown(ev) {
    if (ev.key === "Enter" && this.state.productSearchTerm) {
      const topMatch = this.filteredProducts[0];
      if (topMatch) {
        this.selectProduct(topMatch);
        ev.preventDefault();
      }
    }
  }

  selectPartner(p) {
    console.log("POS Planning Popup: Selecting individual partner:", p);
    this.state.partner_id = p.id;
    this.state.partnerSearchTerm = p.name;
    this.state.phone = p.phone || "";
    this.state.showPartnerList = false;
  }

  getProduct(id) {
    return this.props.products.find((p) => p.id == id) || { display_name: id, lst_price: 0 };
  }

  removeProduct(id) {
    this.state.booking_line_ids = this.state.booking_line_ids.filter(
      (sid) => sid !== id,
    );
  }

  cancel() {
    this.props.close();
  }

  async save(andCopy = false) {

    console.log("POS Planning Popup: Save button clicked. Current state:", {
      partner_id: this.state.partner_id,
      partnerSearchTerm: this.state.partnerSearchTerm,
      phone: this.state.phone,
      booking_line_ids: [...(this.state.booking_line_ids || [])],
      is_available_slot: this.state.is_available_slot
    });
    const p = {
      start_datetime: this.localInputToUTC(this.state.start_datetime),
      end_datetime: this.localInputToUTC(this.state.end_datetime),
      resource_id: parseInt(this.state.resource_id) || false,
      role_id: parseInt(this.state.role_id) || false,
      name: this.state.name,
      is_available_slot: this.state.is_available_slot,
      booking_line_ids: [...(this.state.booking_line_ids || [])],
      booking_status: this.state.booking_status,
      partner_id: this.state.partner_id,
      partnerSearchTerm: this.state.partnerSearchTerm,
      phone: this.state.phone,
      copy_partner: andCopy || false,
    };
    console.log("POS Planning Popup: Handing over payload to parent:", p);
    await this.props.getPayload(p);

    console.log("POS Planning Popup: Parent finished processing payload. Closing.");
    this.props.close();
  }

  onDelete() {
    if (this.state.showDeleteConfirm) {
      this.props.getPayload(null);
      this.props.close();
    } else this.state.showDeleteConfirm = true;
  }
}
