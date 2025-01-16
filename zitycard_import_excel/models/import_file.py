import base64
import os
import tempfile

import pandas as pd
import io

import requests
from odoo import api, models, fields, _


class ImportFile(models.Model):
    _name = 'import.file'
    _description = 'import files'

    name = fields.Char(string='Nombre')
    active = fields.Boolean(string='Active')
    url_file = fields.Char(string='Url archivo')
    column_mapping_ids = fields.One2many('column.mapping.import', 'import_file_id', string='Columnas')
    model = fields.Selection([('helpdesk.ticket', 'Tickets')], string='Modelo', required=True)
    record_ids = fields.Char(string='Record IDs', copy=False)
    rendered_records = fields.Text(string='Rendered Records', compute='_compute_rendered_records')
    order_by = fields.Char(string='Ordenar por')
    start_number = fields.Integer(string='Empezar el')

    @api.depends('model', 'record_ids')
    def _compute_rendered_records(self):
        """Computa los registros creados por la importación, con el modelo correspondiente"""
        for record in self:
            if record.model and record.record_ids:
                # Convertir la cadena de IDs en una lista de enteros, eliminando elementos vacíos
                ids_list = [int(id.strip()) for id in record.record_ids.split(',') if id.strip()]
                # Obtener el modelo dinámicamente
                model = self.env[record.model]
                # Buscar los registros y renderizarlos
                records = model.browse(ids_list)
                rendered_text = "\n".join([str(rec) for rec in records])
                record.rendered_records = rendered_text
            else:
                record.rendered_records = ''

    def action_open_records(self):
        """Muestra los registros creados por el importador"""
        for record in self:
            if record.model and record.record_ids:
                ids_list = [int(id.strip()) for id in record.record_ids.split(',') if id.strip()]
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Records',
                    'res_model': record.model,
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', ids_list)],
                }

    def import_files(self):
        import_file_ids = self.search([('active', '=', True)])
        for import_file_id in import_file_ids:
            import_file_id.read_and_create(import_file_id)

    def import_file(self):
        self.read_and_create(self)

    @api.model
    def read_and_create(self, import_file_id):
        # URL del archivo Excel
        excel_url = import_file_id.url_file

        try:
            # Descargar el archivo Excel
            response = requests.get(excel_url, timeout=30)
            response.raise_for_status()

            # Guardar el archivo en el directorio de datos de Odoo
            data_dir = self.env['ir.config_parameter'].sudo().get_param('data_dir', '/var/lib/odoo')
            temp_file_path = os.path.join(data_dir, 'temp_excel_file.xlsx')

            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(response.content)

            # Leer el archivo Excel con pandas
            df = pd.read_excel(temp_file_path, engine='openpyxl')

            # Ordenar por ids del excel
            df = df.sort_values(by="Secuencia de los IDs de tickets", ascending=True)
            # Eliminar el archivo temporal después de procesarlo
            os.remove(temp_file_path)

            # Verificar si hay datos
            if df.empty:
                raise ValueError("El archivo Excel está vacío.")

            # Crear tickets basados en las filas
            fila = 0
            for index, row in df.iterrows():
                fila = int(row.get(import_file_id.order_by))
                if import_file_id.order_by and fila < import_file_id.start_number:
                    continue
                else:
                    vals = {}
                    column_mapping_ids = import_file_id.column_mapping_ids.filtered(lambda l: l.active_import)
                    for columna in column_mapping_ids:
                        if row.get(columna.name):
                            if columna.field_type == 'char':
                                vals[columna.field_name] = str(row.get(columna.name))
                            if columna.field_type == 'many2one':
                                res_id = self.env[columna.model_field].sudo().search([(columna.match_field, '=', str(row.get(columna.name)))])
                                vals[columna.field_name] = res_id.id
                    res = self.env[import_file_id.model].create(vals)
                    if import_file_id.record_ids:
                        import_file_id.record_ids = import_file_id.record_ids + ',' + str(res.id)
                    else:
                        import_file_id.record_ids = str(res.id)
            if fila != 0:
                import_file_id.start_number = fila + 1
        except Exception as e:
            raise Exception(_("Error al procesar el archivo Excel: %s") % str(e))


class ColumnMappingImport(models.Model):
    _name = 'column.mapping.import'
    _description = 'Columnas de mapeo para el documento a importar'

    name = fields.Char(string='Columna CSV')
    field_name = fields.Char(string='Nombre del campo')
    field_type = fields.Selection([('char', 'String'),
                                   ('many2one', 'Many2one'),
                                   ], String='Tipo de Campo', default='char')
    model_field = fields.Char(string="Modelo del campo Many2one")
    match_field = fields.Char(string="Campo de búsqueda Many2one")
    import_file_id = fields.Many2one(comodel_name='import.file', string='Import CSV')
    active_import = fields.Boolean(string='Activo')
