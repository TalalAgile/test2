odoo.define(
  "@mail/views/web/fields/avatar/avatar",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class Avatar extends Component {}
    Avatar.template = "mail.Avatar";
    Avatar.props = {
      resModel: { type: String, optional: true },
      resId: { type: Number, optional: true },
      displayName: { type: String, optional: true },
      noSpacing: { type: Boolean, optional: true },
      cssClass: { type: String, optional: true },
      onClickAvatar: { type: Function, optional: true },
      showPopover: { type: Boolean, optional: true },
    };
    return { Avatar };
  },
);

odoo.define(
  "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class AvatarCardResourcePopover extends Component {}
    AvatarCardResourcePopover.template =
      "resource_mail.AvatarCardResourcePopover";
    AvatarCardResourcePopover.props = {
      id: { type: Number, optional: true },
      recordModel: { type: String, optional: true },
      slots: { type: Object, optional: true },
    };
    return { AvatarCardResourcePopover };
  },
);

odoo.define(
  "@resource_mail/views/fields/many2one_avatar_resource/many2one_avatar_resource_field",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class Many2OneAvatarResourceField extends Component {}
    Many2OneAvatarResourceField.template =
      "resource_mail.Many2OneAvatarResourceField";
    Many2OneAvatarResourceField.props = {
      readonly: { type: Boolean, optional: true },
      name: { type: String, optional: true },
      record: { type: Object, optional: true },
    };
    return {
      Many2OneAvatarResourceField,
      many2OneAvatarResourceField: {
        fieldDependencies: [],
      },
    };
  },
);

odoo.define(
  "@resource_mail/views/fields/many2one_avatar_resource/kanban_many2one_avatar_resource_field",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class KanbanMany2OneAvatarResourceField extends Component {}
    KanbanMany2OneAvatarResourceField.template =
      "resource_mail.KanbanMany2OneAvatarResourceField";
    KanbanMany2OneAvatarResourceField.props = {
      readonly: { type: Boolean, optional: true },
      name: { type: String, optional: true },
      record: { type: Object, optional: true },
    };
    return {
      KanbanMany2OneAvatarResourceField,
      kanbanMany2OneAvatarResourceField: {
        fieldDependencies: [],
      },
    };
  },
);

odoo.define(
  "@resource_mail/views/fields/many2many_avatar_resource/many2many_avatar_resource_field",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class Many2ManyAvatarResourceField extends Component {}
    Many2ManyAvatarResourceField.props = {
      readonly: { type: Boolean, optional: true },
      name: { type: String, optional: true },
      record: { type: Object, optional: true },
    };
    return {
      Many2ManyAvatarResourceField,
      many2ManyAvatarResourceField: {
        fieldDependencies: [],
        relatedFields: () => [],
      },
    };
  },
);

odoo.define(
  "@hr/components/avatar_card_employee/avatar_card_employee_popover",
  ["@odoo/owl"],
  function (require) {
    "use strict";
    const { Component } = require("@odoo/owl");
    class AvatarCardEmployeePopover extends Component {}
    AvatarCardEmployeePopover.template = "hr.AvatarCardEmployeePopover";
    AvatarCardEmployeePopover.props = {
      id: { type: Number, optional: true },
    };
    return { AvatarCardEmployeePopover };
  },
);
