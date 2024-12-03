import re

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.depends("comercial")
    @api.depends_context("no_display_commercial")
    def _compute_display_name(self):
        name_pattern = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("l10n_es_partner.name_pattern", default="")
        )
        no_display_commercial = self.env.context.get("no_display_commercial")
        for partner in self:
            if no_display_commercial or not name_pattern or not partner.comercial:
                super(ResPartner, partner)._compute_display_name()
            else:
                name = name_pattern % {
                    "name": partner.complete_name,
                    "comercial_name": partner.comercial if partner.comercial else '',
                }

                # name = partner.with_context(lang=self.env.lang)._get_complete_name()
                if partner._context.get('show_address'):
                    name = name + "\n" + partner._display_address(without_company=True)
                name = re.sub(r'\s+\n', '\n', name)
                if partner._context.get('partner_show_db_id'):
                    name = f"{name} ({partner.id})"
                if partner._context.get('address_inline'):
                    splitted_names = name.split("\n")
                    name = ", ".join([n for n in splitted_names if n.strip()])
                if partner._context.get('show_email') and partner.email:
                    name = f"{name} <{partner.email}>"
                if partner._context.get('show_vat') and partner.vat:
                    name = f"{name} ‒ {partner.vat}"

                partner.display_name = name.strip()
        return True
