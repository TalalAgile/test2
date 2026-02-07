/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PlanningBooking = publicWidget.Widget.extend({
  selector: "#wrap",
  events: {
    "click .location-card": "_onLocationSelect",
    "click .service-card": "_onServiceToggle",
    "click .professional-card": "_onProfessionalSelect",
    "change .per-service-resource-select": "_onPerServiceResourceChange",
    "click .date-item": "_onDateSelect",
    "click .time-slot": "_onTimeSelect",
    "click .back-btn": "_onBack",
    "click #final_confirm_btn": "_onFinalConfirm",
    "click #services_continue_btn": "_onServicesContinue",
    "click #per_service_continue_btn": "_onPerServiceContinue",
  },

  init() {
    this._super(...arguments);
    this.bookingData = {
      location: null,
      products: [],
      resource_mode: "any",
      date: null,
      time: null,
    };
  },

  start() {
    if (!this.$el.find(".booking-steps").length) return Promise.resolve();
    this._initDatePicker();
    return this._super(...arguments);
  },

  _onLocationSelect(ev) {
    const $card = $(ev.currentTarget);
    const locationId = $card.data("location-id");
    this.bookingData.location = {
      id: locationId,
      name: $card.data("location-name"),
    };

    // Filter professionals based on location
    this.$('.professional-card[data-mode="single"]').each(function () {
      const $prof = $(this);
      const posIds = $prof.data("pos-config-ids");
      if (posIds) {
        const ids = String(posIds)
          .split(",")
          .map((id) => parseInt(id.trim()));
        $prof.toggleClass("d-none", !ids.includes(locationId));
      }
    });

    this._updateSidebar();
    this._goToStep(2);
  },

  _onServiceToggle(ev) {
    const $card = $(ev.currentTarget);
    const pid = $card.data("product-id");
    if ($card.hasClass("border-primary")) {
      $card
        .removeClass("border-primary shadow-lg")
        .addClass("border-transparent");
      $card.find(".fa-check-circle").remove();
      this.bookingData.products = this.bookingData.products.filter(
        (p) => p.id !== pid,
      );
    } else {
      $card
        .addClass("border-primary shadow-lg")
        .removeClass("border-transparent");
      $card.append(
        '<i class="fa fa-check-circle position-absolute top-0 end-0 m-2 text-primary fs-4"/>',
      );
      this.bookingData.products.push({
        id: pid,
        name: $card.data("product-name"),
        price: parseFloat($card.data("product-price")) || 0,
        duration: $card.data("duration") || 15,
        resource: { id: 0, name: "Any professional" },
      });
    }
    this.$("#services_continue_btn").toggleClass(
      "d-none",
      this.bookingData.products.length === 0,
    );
    this._updateSidebar();
  },

  _onServicesContinue() {
    this._goToStep(3);
  },

  _onProfessionalSelect(ev) {
    const $card = $(ev.currentTarget);
    const mode = $card.data("mode");
    this.bookingData.resource_mode = mode;
    if (mode === "single") {
      const rid = $card.data("resource-id");
      const rname = $card.data("resource-name");
      this.bookingData.products.forEach(
        (p) => (p.resource = { id: rid, name: rname }),
      );
      this._goToStep(4);
    } else if (mode === "any") {
      this.bookingData.products.forEach(
        (p) => (p.resource = { id: 0, name: "Any professional" }),
      );
      this._goToStep(4);
    } else if (mode === "per_service") {
      this._renderPerServiceView();
    }
    this._updateSidebar();
  },

  _renderPerServiceView() {
    this.$(".professional-options-grid").addClass("d-none");
    this.$("#per_service_selection_container").removeClass("d-none");
    let html = "";
    const resources = [];
    this.$('.professional-card[data-mode="single"]:not(.d-none)').each(
      function () {
        resources.push({
          id: $(this).data("resource-id"),
          name: $(this).data("resource-name"),
          avatar: $(this).find("img").attr("src"),
        });
      },
    );
    this.bookingData.products.forEach((p) => {
      const selectedRes = p.resource?.id ? resources.find(r => r.id == p.resource.id) : null;
      html += `
        <div class="card mb-4 shadow-sm border-0 rounded-4 bg-white specialist-selection-card">
          <div class="card-body p-4 d-flex align-items-center justify-content-between">
            <div class="service-info">
              <h4 class="fw-bold mb-1 text-dark">${p.name}</h4>
              <div class="text-muted small">${p.duration} min</div>
            </div>
            
            <div class="professional-selector-pill d-flex align-items-center gap-2 p-2 px-3 border rounded-pill bg-light hover-shadow transition pointer" 
                 data-pid="${p.id}" onclick="window.openSpecialistModal(this)">
                <div class="avatar-circle rounded-circle bg-white d-flex align-items-center justify-content-center border shadow-sm" style="width: 36px; height: 36px; overflow: hidden;">
                    <img src="${selectedRes?.avatar || '/web/static/img/user_menu_avatar.png'}" style="width: 100%; height: 100%; object-fit: cover;"/>
                </div>
                <div class="d-flex flex-column text-start">
                    <span class="text-muted" style="font-size: 0.7rem; line-height: 1;">Specialist</span>
                    <span class="fw-bold text-dark" style="font-size: 0.95rem;">${selectedRes?.name || "Select..."}</span>
                </div>
                <i class="fa fa-chevron-right ms-2 text-muted small"></i>
            </div>
          </div>
        </div>`;
    });
    this.$("#per_service_list").html(html);

    // Modal Global Helpers
    window.openSpecialistModal = (el) => {
      const pid = $(el).data('pid');
      const prod = this.bookingData.products.find(p => p.id == pid);

      let modalHtml = `
            <div class="specialist-modal-overlay" onclick="window.closeSpecialistModal(event)">
                <div class="specialist-modal-container" onclick="event.stopPropagation()">
                    <div class="specialist-modal-header d-flex justify-content-between align-items-center">
                        <div>
                            <h4 class="fw-bold mb-0">Choose Specialist</h4>
                            <p class="text-muted small mb-0">For ${prod.name}</p>
                        </div>
                        <button class="btn btn-close text-dark" onclick="window.closeSpecialistModal()"></button>
                    </div>
                    <div class="specialist-list">
                        <div class="specialist-item border-bottom" onclick="window.selectResourceFromModal(${pid}, 0, 'Any professional')">
                            <div class="bg-light rounded-circle d-flex align-items-center justify-content-center text-secondary" style="width: 56px; height: 56px;">
                                <i class="fa fa-users fs-3"></i>
                            </div>
                            <div>
                                <h5 class="fw-bold mb-0 text-dark">Any professional</h5>
                                <span class="text-muted small">Recommended for fastest booking</span>
                            </div>
                        </div>
                        ${resources.map(r => `
                            <div class="specialist-item border-bottom" onclick="window.selectResourceFromModal(${pid}, ${r.id}, '${r.name}', '${r.avatar}')">
                                <img src="${r.avatar}" />
                                <div>
                                    <h5 class="fw-bold mb-0 text-dark">${r.name}</h5>
                                    <span class="text-muted small">Available professional</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>`;
      $('body').append(modalHtml);
      $('body').css('overflow', 'hidden');
    };

    window.closeSpecialistModal = (e) => {
      if (e && e.target !== e.currentTarget && !$(e.target).hasClass('btn-close')) return;
      $('.specialist-modal-overlay').remove();
      $('body').css('overflow', '');
    };

    window.selectResourceFromModal = (pid, rid, rname, avatar) => {
      const prod = this.bookingData.products.find(p => p.id == pid);
      if (prod) {
        prod.resource = { id: rid, name: rname };
        const $pill = $(`.professional-selector-pill[data-pid="${pid}"]`);
        $pill.find('img').attr('src', avatar || '/web/static/img/user_menu_avatar.png');
        $pill.find('.fw-bold').text(rname);
        this._updateSidebar();
      }
      window.closeSpecialistModal();
    };
  },

  _onPerServiceResourceChange(ev) {
    const pid = $(ev.currentTarget).data("product-id");
    const rid = parseInt($(ev.currentTarget).val());
    const rname = $(ev.currentTarget).find("option:selected").text();
    const prod = this.bookingData.products.find((p) => p.id === pid);
    if (prod) prod.resource = { id: rid, name: rname };
    this._updateSidebar();
  },

  _onPerServiceContinue() {
    this._goToStep(4);
  },

  _onDateSelect(ev) {
    const $item = $(ev.currentTarget);
    this.$(".date-item")
      .removeClass("active border-primary text-primary shadow-lg")
      .addClass("bg-white");
    $item
      .addClass("active border-primary text-primary shadow-lg")
      .removeClass("bg-white");
    this.bookingData.date = $item.data("date");
    this._loadTimeSlots();
  },

  _onTimeSelect(ev) {
    const $slot = $(ev.currentTarget);
    this.$(".time-slot").removeClass(
      "bg-primary text-white border-primary shadow-lg",
    );
    $slot.addClass("bg-primary text-white border-primary shadow-lg");
    this.bookingData.time = {
      display: $slot.data("time"),
      start: $slot.data("full-start"),
      assignments: $slot.data("assignments"),
    };
    this.$("#sidebar_continue")
      .removeAttr("disabled")
      .removeClass("opacity-50")
      .addClass("btn-dark");
    this._goToStep(5);
  },

  async _loadTimeSlots() {
    this.$("#time_slots_container").html(
      '<div class="text-center py-5"><i class="fa fa-spinner fa-spin fs-2 text-muted"/></div>',
    );
    try {
      const pairs = this.bookingData.products.map((p) => ({
        product_id: p.id,
        res_id: p.resource.id,
      }));
      const slots = await rpc("/planning/get_available_slots", {
        date: this.bookingData.date,
        product_res_pairs: pairs,
        location_id: this.bookingData.location.id,
      });
      let html =
        slots.length > 0
          ? ""
          : '<div class="text-center py-5 text-muted">No availability found for this selection.</div>';
      slots.forEach((s) => {
        html += `<div class="time-slot p-3 bg-white rounded-3 border-0 shadow-sm mb-3 d-flex justify-content-between align-items-center transition pointer"
                                 data-time="${s.start}" data-full-start="${s.full_start}" data-assignments='${JSON.stringify(s.assignments)}'>
                                <div>
                                    <div class="fw-bold fs-4 text-dark lh-1">${s.start}</div>
                                    <div class="text-muted small mt-1">${s.duration} min</div>
                                </div>
                                <div class="text-end">
                                    <div class="small fw-bold text-dark">${s.assignments.map((a) => `<span class="text-warning">${this.bookingData.products.find((p) => p.id === a.prod_id)?.name || ""}</span> <span class="text-primary">${a.res_name}</span>`).join(" <span class='text-muted mx-1'>-></span> ")}</div>
                                    <div class="text-muted text-uppercase mt-1" style="font-size: 9px; letter-spacing: 0.5px;">Professional Sequence</div>
                                </div>
                            </div>`;
      });
      this.$("#time_slots_container").html(html);
    } catch (e) { }
  },

  async _onFinalConfirm() {
    const name = this.$("#confirm_name").val();
    const phone = this.$("#confirm_phone").val();
    const countryId = this.$("#confirm_country").val();
    if (!name || !phone) return alert("Required fields missing");
    this.$("#final_confirm_btn")
      .attr("disabled", "disabled")
      .html('<i class="fa fa-spinner fa-spin me-2"/>Processing...');
    try {
      const res = await rpc("/planning/confirm_booking", {
        assignments: this.bookingData.time.assignments,
        start_time: this.bookingData.time.start,
        partner_name: name,
        phone: phone,
        location_id: this.bookingData.location.id,
        country_id: countryId || null,
      });
      if (res.success)
        window.location.href = `/planning/booking/success?order_name=${res.order_name}`;
      else {
        alert(res.error);
        this.$("#final_confirm_btn")
          .removeAttr("disabled")
          .text("Confirm Booking");
      }
    } catch (e) {
      alert("An error occurred: " + (e.message || "Unknown error"));
      this.$("#final_confirm_btn")
        .removeAttr("disabled")
        .text("Confirm Booking");
    }
  },

  _onBack(ev) {
    const current = $(ev.currentTarget).data("back-to");
    if (
      current === 2 &&
      !this.$("#per_service_selection_container").hasClass("d-none")
    ) {
      this.$("#per_service_selection_container").addClass("d-none");
      this.$(".professional-options-grid").removeClass("d-none");
    } else {
      this._goToStep(current);
    }
  },

  _goToStep(step) {
    this.$(".booking-step").addClass("d-none");
    this.$(`#step_${step}`).removeClass("d-none");
    this.$(".step-item")
      .removeClass("active border-bottom border-3 border-primary opacity-100")
      .addClass("opacity-50");
    this.$(`.step-item[data-step="${step}"]`)
      .addClass("active border-bottom border-3 border-primary opacity-100")
      .removeClass("opacity-50");
    if (step === 4 && !this.bookingData.date)
      this.$(".date-item").first().click();
    if (step === 5) this._renderFinalSummary();
    window.scrollTo(0, 0);
  },

  _updateSidebar() {
    let html = "";
    if (this.bookingData.location)
      html += `<div class="d-flex justify-content-between small mb-3 border-bottom pb-2"><span>Location:</span><span class="fw-bold text-dark">${this.bookingData.location.name}</span></div>`;
    let total = 0;
    this.bookingData.products.forEach((p) => {
      html += `
        <div class="mb-4">
            <div class="d-flex justify-content-between align-items-start mb-1">
                <span class="fw-bold text-dark" style="max-width: 70%;">${p.name}</span>
                <span class="fw-bold text-dark text-nowrap">JOD ${p.price.toFixed(1)}</span>
            </div>
            ${p.resource ? `<div class="text-dark d-flex align-items-center gap-1" style="font-size: 0.9rem;">
                <span class="fw-bold">${p.resource.name}</span>
            </div>` : ""}
        </div>`;
      total += p.price;
    });
    this.$("#sidebar_items").html(html);
    this.$("#side_subtotal, #side_total").text(
      `JOD ${total.toLocaleString(undefined, { minimumFractionDigits: 1 })}`,
    );
  },
  _initDatePicker() {
    /* Same */ const $container = this.$("#date_picker_container");
    if (!$container.length) return;
    const now = new Date();
    let html = "";
    for (let i = 0; i < 21; i++) {
      const d = new Date();
      d.setDate(now.getDate() + i);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      const dateStr = `${year}-${month}-${day}`;
      html += `<div class="date-item flex-shrink-0 text-center p-3 rounded-circle border bg-white pointer shadow-sm transition" style="width: 75px; min-width: 75px;" data-date="${dateStr}"><div class="x-small text-uppercase opacity-50" style="font-size: 10px;">${d.toLocaleDateString(undefined, { weekday: "short" })}</div><div class="fw-bold fs-5">${d.getDate()}</div></div>`;
    }
    $container.html(html);
  },
  _renderFinalSummary() {
    let sHtml = this.bookingData.products
      .map(
        (p) =>
          `<div>• ${p.name} - <b>${p.resource ? p.resource.name : "Any"}</b></div>`,
      )
      .join("");
    this.$("#summary_content").html(
      `<div class="d-flex flex-column gap-3 p-4 bg-light rounded-4 shadow-sm border"><div><span class="text-muted small fw-bold uppercase text-uppercase">Services & Specialists:</span><br/><div class="mt-2">${sHtml}</div></div><div class="d-flex justify-content-between border-top pt-3"><span>Appointment Date:</span><span class="fw-bold text-dark">${this.bookingData.date}</span></div><div class="d-flex justify-content-between"><span>Branch Location:</span><span class="fw-bold text-dark">${this.bookingData.location.name}</span></div><div class="d-flex justify-content-between border-top pt-3"><span>Sequence Starts:</span><span class="fw-bold text-primary fs-4">${this.bookingData.time.display}</span></div></div>`,
    );
  },
});
