from odoo import api, models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Documentos de portal',
        domain="[('res_model', '=', 'res.partner'), ('res_id', '=', id)]",
        help="Attachments related to this partner."
    )

    def write(self, vals):
        res = super().write(vals)
        if 'attachment_ids' in vals :
            for attachment_id in self.attachment_ids:
                if not attachment_id.access_token:
                    attachment_id.generate_access_token()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for partner_id in res:
            if partner_id.attachment_ids:
                for attachment_id in partner_id.attachment_ids:
                    attachment_id.generate_access_token()
        return res
