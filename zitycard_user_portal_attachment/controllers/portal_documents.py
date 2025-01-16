from odoo import conf, http, _
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class ProjectCustomerPortalDocuments(CustomerPortal):

    @http.route(['/odoo/user_documents'], type='http', auth="user", website=True)
    def portal_my_projects(self, **kw):
        values = self._prepare_portal_layout_values()
        partner_id = request.env.user.partner_id
        attachment_ids = partner_id.attachment_ids

        values.update({
            'attachment_ids': attachment_ids,
            'default_url': '/odoo/user_documents',
        })
        return request.render("zitycard_user_portal_attachment.portal_my_documents", values)
