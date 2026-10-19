from odoo import http
from odoo.http import request, content_disposition

class SAFTAOController(http.Controller):

    @http.route('/web/download/saft_ao_file/<int:saft_id>', type='http', auth='user')
    def download(self, saft_id, **kwargs):
        result = request.env["saft.ao.file.export"].browse(saft_id)
        if not result.exists():
            return request.not_found()
        result.ensure_one()
        result.check_access_rights('read')
        result.check_access_rule('read')
        headers = [
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', content_disposition(f"{result.name}.xml"))
        ]
        return request.make_response(result.content_xml, headers=headers)

