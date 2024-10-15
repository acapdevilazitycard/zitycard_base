import base64
import xmlrpc.client
from odoo import models, fields, api
_logger = logging.getLogger(__name__)

class CRMTransfer(models.TransientModel):
    _name = 'crm.transfer'
    _description = 'Transferir datos de CRM entre bases de datos con verificación de duplicados y tablas intermedias'

    source_db = fields.Char(string='Base de Datos Origen', required=True, default='Zitycard')
    source_host_db = fields.Char(string='Host Base de Datos Origen', required=True, default='https://zitycard.com')
    source_user = fields.Char(string='Usuario BD Origen Destino', required=True, default='acapdevila@zitycard.com')
    source_password = fields.Char(string='Contraseña BD Origen', required=True, default='Mercecayuela95')

    def _get_source_connection(self):
        """Crea una conexión a la base de datos de origen utilizando la API de Odoo."""
        return xmlrpc.client.ServerProxy(f'{self.source_host_db}/xmlrpc/2/common'), \
            xmlrpc.client.ServerProxy(f'{self.source_host_db}/xmlrpc/2/object')

    def _get_uid(self):
        """Obtiene el UID del usuario para la conexión a la base de datos de origen."""
        common, _ = self._get_source_connection()
        return common.authenticate(self.source_db, self.source_user, self.source_password, {})

    def _record_exists_by_name(self, table, name):
        """Comprueba si un registro ya existe en la base de datos de destino utilizando el nombre."""
        return self.env[table].with_context(lang='en_US').search([('name', '=', name)], limit=1)

    def _insert_if_not_exists_by_name(self, table, name, vals):
        """Inserta un registro si no existe en la base de datos destino usando el nombre."""
        record_exists = self._record_exists_by_name(table, name)

        if not record_exists:
            return self.env[table].sudo().create(vals)
        return record_exists

    def _insert_direct(self, table, vals):
        """Inserta un registro si no existe en la base de datos destino usando el nombre."""
        return self.env[table].sudo().create(vals)

    def _get_or_create_user(self, user_name):
        """Busca el usuario por nombre; si no existe, crea un contacto y un usuario asociado."""
        user = self._record_exists_by_name('res.users', user_name)
        if not user:
            # Crear un contacto asociado si no existe
            partner_vals = {'name': user_name}
            partner = self._insert_if_not_exists_by_name('res.partner', user_name, partner_vals)

            # Crear el usuario con el contacto asociado
            user_vals = {
                'name': user_name,
                'login': user_name,  # Ajustar el campo login según necesidad
                'partner_id': partner.id,
            }
            user = self.env['res.users'].sudo().create(user_vals)
        return user

    def _get_or_create_categories(self, category_names):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        category_ids = []
        for category_name in category_names:
            category = self._record_exists_by_name('res.partner.category', category_name)
            if not category:
                category = self.env['res.partner.category'].sudo().create({'name': category_name})
            category_ids.append(category.id)
        return category_ids

    def _get_employees(self, employees):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        employee_ids = []
        for employee_id in employees:
            employee = self._record_exists_by_name('hr.employee', employee_id)
            if not employee:
                employee = self.env['hr.employee'].sudo().create({'name': employee_id})
            employee_ids.append(employee.id)
        return employee_ids

    def _get_team_ids(self, teams_names):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        team_ids = []
        for team_name in teams_names:
            team = self._record_exists_by_name('helpdesk.team', team_name)
            if not team:
                team = self.env['helpdesk.team'].sudo().create({'name': team_name})
            team_ids.append(team.id)
        return team_ids

    def _get_helpdesk_tag_ids(self, tag_names):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        tag_ids = []
        for tag_name in tag_names:
            team = self._record_exists_by_name('helpdesk.tag', tag_name)
            if not team:
                team = self.env['helpdesk.tag'].sudo().create({'name': tag_name})
            tag_ids.append(team.id)
        return tag_ids

    def _get_m2m(self, model, res_ids, vals):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        tag_ids = []
        for res_id in res_ids:
            res_add = self._record_exists_by_name(model, res_id['name'])
            if not res_add:
                if vals:
                    uid = self._get_uid()
                    _, obj = self._get_source_connection()
                    res_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                             model, 'search_read', [[['id', '=', res_id['id']]]], {'fields': vals})
                    create_vals = {}
                    for val in vals:
                        create_vals[val] = res_ids[0][val]
                res_add = self.env[model].sudo().create(create_vals)
            tag_ids.append(res_add.id)
        return tag_ids

    def _get_or_create_employee_categories(self, category_names):
        """Busca las categorías por nombre, las crea si no existen y devuelve sus IDs."""
        category_ids = []
        for category_name in category_names:
            category = self._record_exists_by_name('hr.employee.category', category_name)
            if not category:
                category = self.env['hr.employee.category'].sudo().create({'name': category_name})
            category_ids.append(category.id)
        return category_ids

    def _get_or_create_team(self, team_name):
        """Busca el equipo por nombre; si no existe, lo crea en crm.team."""
        team = self._record_exists_by_name('crm.team', team_name)
        if not team:
            team_vals = {'name': team_name}
            team = self.env['crm.team'].sudo().create(team_vals)
        return team

    def _get_or_create_stage(self, stage_name):
        """Busca la etapa por nombre; si no existe, la crea en crm.stage."""
        stage = self._record_exists_by_name('crm.stage', stage_name)
        if not stage:
            stage_vals = {'name': stage_name}
            stage = self.env['crm.stage'].sudo().create(stage_vals)
        return stage

    def _get_or_create_partner(self, partner_name):
        """Busca la etapa por nombre; si no existe, la crea en crm.stage."""
        partner = self._record_exists_by_name('res.partner', partner_name)
        if not partner:
            partner_vals = {'name': partner_name}
            partner = self.env['res.partner'].sudo().create(partner_vals)
        return partner

    def _get_or_create_stage_id(self, stage_name):
        """Busca la etapa por nombre; si no existe, la crea en crm.stage."""
        stage = self._record_exists_by_name('helpdesk.stage', stage_name)
        if not stage:
            stage_vals = {'name': stage_name}
            stage = self.env['helpdesk.stage'].sudo().create(stage_vals)
        return stage

    def _get_or_create_source(self, source_name):
        """Busca la etapa por nombre; si no existe, la crea en crm.stage."""
        source = self._record_exists_by_name('res.partner', source_name)
        if not source:
            source_vals = {'name': source_name}
            source = self.env['utm.source'].sudo().create(source_vals)
        return source

    def _get_or_create_department(self, department_name):
        """Busca o crea un departamento por nombre."""
        department = self._record_exists_by_name('hr.department', department_name)
        if not department:
            department = self.env['hr.department'].sudo().create({'name': department_name})
        return department

    def _get_or_create_helpdesk_team(self, helpdesk_team_name):
        """Busca o crea un departamento por nombre."""
        team = self._record_exists_by_name('helpdesk.team', helpdesk_team_name)
        if not team:
            team = self.env['helpdesk.team'].sudo().create({'name': helpdesk_team_name})
        return team

    def _get_or_create_many2one(self, model, res_id, vals=False):
        """Busca o crea un departamento por nombre."""
        res = self._record_exists_by_name(model, res_id[1])
        if not res:
            if vals:
                uid = self._get_uid()
                _, obj = self._get_source_connection()
                res_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                         model, 'search_read', [[['id', '=', res_id[0]]]], {'fields': vals})
                if res_ids[0]:
                    create_vals = {}
                    for val in vals:
                        create_vals[val] = res_ids[0][val]
                    res = self.env[model].sudo().create(create_vals)
                else:
                    res = self.env[model].sudo().create({'name': res_id[1]})
            else:
                res = self.env[model].sudo().create({'name': res_id[1]})
        return res

    def _get_or_create_job_position(self, job_name):
        """Busca o crea un puesto de trabajo por nombre."""
        job_position = self._record_exists_by_name('hr.job', job_name)
        if not job_position:
            job_position = self.env['hr.job'].sudo().create({'name': job_name})
        return job_position

    def _get_or_create_employee(self, employee_name):
        """Busca o crea un empleado por nombre."""
        employee = self._record_exists_by_name('hr.employee', employee_name)
        if not employee:
            employee_vals = {'name': employee_name}
            employee = self.env['hr.employee'].sudo().create(employee_vals)
        return employee

    def _get_or_create_holiday_status_id(self, hr_leave_type_name):
        """Busca o crea un empleado por nombre."""
        hr_leave_type = self._record_exists_by_name('hr.leave.type', hr_leave_type_name)
        if not hr_leave_type:
            hr_leave_type_vals = {'name': hr_leave_type_name}
            hr_leave_type = self.env['hr.employee'].sudo().create(hr_leave_type_vals)
        return hr_leave_type

    def transfer_data_res_partner(self):
        """Transferencia de datos entre bases de datos usando la API de Odoo y manejo por nombre."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir contactos (res.partner)
        partner_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                     'res.partner', 'search', [[]])
        partners = obj.execute_kw(self.source_db, uid, self.source_password,
                                  'res.partner', 'read', [partner_ids],
                                  {'fields': ['id', 'name', 'type', 'company_id', 'email', 'phone', 'street', 'street2',
                                              'city', 'state_id', 'zip', 'country_id', 'function', 'comment',
                                              'website', 'category_id', 'user_id', 'active', 'create_date',
                                              'write_date', 'vat', 'credit_limit', 'debit_limit', 'currency_id',
                                              'is_company', 'type', 'message_ids']})

        for partner in partners:
            # Buscar o crear el usuario asociado
            user_id = partner['user_id'] and partner['user_id'][1]  # Obtener el nombre del usuario si existe
            user = self._get_or_create_user(user_id) if user_id else False
            category_ids = False
            # Obtener las categorías por nombre (si existen) o crearlas
            if partner['category_id']:
                category_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'res.partner.category', 'search_read',
                                              [[['id', 'in', partner['category_id']]]], {'fields': ['name', 'color']})
                category_names = [cat['name'] for cat in category_ids] if category_ids else []
                category_ids = self._get_or_create_categories(category_names)

            vals = {
                'name': partner['name'],
                'type': partner['type'],
                'company_id': partner['company_id'][0] if partner['company_id'] else False,
                'email': partner['email'],
                'phone': partner['phone'],
                'street': partner['street'],
                'street2': partner['street2'],
                'city': partner['city'],
                'state_id': partner['state_id'][0] if partner['state_id'] else False,
                'zip': partner['zip'],
                'country_id': partner['country_id'][0] if partner['country_id'] else False,
                'function': partner['function'],
                'comment': partner['comment'],
                'website': partner['website'],
                'category_id': [(6, 0, category_ids)] if category_ids else False,
                # Many2many categories (replace all existing)
                'user_id': user.id if user else False,
                'active': partner['active'],
                'create_date': partner['create_date'],
                'write_date': partner['write_date'],
                'vat': partner['vat'],
                'credit_limit': partner['credit_limit'],
                'debit_limit': partner['debit_limit'],
                'currency_id': partner['currency_id'][0] if partner['currency_id'] else False,
                'is_company': partner['is_company'],
            }
            print(vals)
            _logger.info(vals)
            res = self._insert_if_not_exists_by_name('res.partner', partner['name'], vals)
            self.transfer_message_ids(partner['message_ids'], 'helpdesk.ticket', res.id)

        return True

    def transfer_data_update_res_partner(self):
        """Transferencia de datos entre bases de datos usando la API de Odoo y manejo por nombre."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir contactos (res.partner)
        partner_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                     'res.partner', 'search', [[['parent_id', '!=', False]]])
        partners = obj.execute_kw(self.source_db, uid, self.source_password,
                                  'res.partner', 'read', [partner_ids],
                                  {'fields': ['id', 'name', 'parent_id']})

        for partner in partners:
            parent = obj.execute_kw(self.source_db, uid, self.source_password,
                                    'res.partner', 'read', [partner['parent_id'][0]],
                                    {'fields': ['id', 'name']})
            partner_id = self.env['res.partner'].search([('name', '=', partner['name'])], limit=1)
            parent_id = self.env['res.partner'].search([('name', '=', parent[0]['name'])], limit=1)
            if partner_id and parent_id:
                vals = {
                    'parent_id': parent_id.id if parent_id else False,
                }
                print(vals)
                _logger.info(vals)
                partner_id.write(vals)

        return True

    def transfer_data_crm(self):
        """Transferencia de datos entre bases de datos usando la API de Odoo y manejo por nombre."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir oportunidades (crm.lead)
        lead_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                  'crm.lead', 'search', [[]])
        leads = obj.execute_kw(self.source_db, uid, self.source_password,
                               'crm.lead', 'read', [lead_ids],
                               {'fields': ['id', 'name', 'active', 'type', 'partner_id', 'user_id', 'probability',
                                           'priority', 'stage_id', 'team_id', 'expected_revenue', 'date_deadline',
                                           'city', 'country_id', 'source_id', 'description', 'create_date',
                                           'write_date', 'message_ids']})

        for lead in leads:
            # Buscar o crear el usuario asociado
            user_id = lead['user_id'] and lead['user_id'][1]  # Obtener el nombre del usuario si existe
            user = self._get_or_create_user(user_id) if user_id else False

            # Buscar o crear el equipo (team_id)
            team_id = lead['team_id'] and lead['team_id'][1]
            team = self._get_or_create_team(team_id) if team_id else False

            # Buscar o crear la etapa (stage_id)
            stage_id = lead['stage_id'] and lead['stage_id'][1]
            stage = self._get_or_create_stage(stage_id) if stage_id else False

            # Buscar o crear el contacto (partner_id)
            partner_id = lead['stage_id'] and lead['stage_id'][1]
            partner = self._get_or_create_partner(partner_id) if partner_id else False

            # Buscar o crear el origen (source_id)
            source_id = lead['source_id'] and lead['source_id'][1]
            source = self._get_or_create_source(source_id) if source_id else False

            vals = {
                'name': lead['name'],
                'active': lead['active'],
                'type': lead['type'],
                'partner_id': partner.id if partner else False,  # Vincular con el contacto
                'user_id': user.id if user else False,
                'probability': lead['probability'],
                'priority': lead['priority'],
                'stage_id': stage.id if stage else False,
                'team_id': team.id if team else False,
                'expected_revenue': lead['expected_revenue'],
                'date_deadline': lead['date_deadline'],
                'city': lead['city'],
                'country_id': lead['country_id'][0] if lead['country_id'] else False,
                'source_id': source.id if source else False,
                'description': lead['description'],
                'create_date': lead['create_date'],
                'write_date': lead['write_date'],
            }
            print(vals)
            _logger.info(vals)
            res = self._insert_if_not_exists_by_name('crm.lead', lead['name'], vals)
            self.transfer_message_ids(lead['message_ids'], 'helpdesk.ticket', res.id)

        return True

    def transfer_data_attendance(self):
        """Transferencia de registros de asistencia (hr.attendance) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (hr.attendance)
        attendance_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                        'hr.attendance', 'search', [[]])
        attendances = obj.execute_kw(self.source_db, uid, self.source_password,
                                     'hr.attendance', 'read', [attendance_ids],
                                     {'fields': ['id', 'display_name', 'employee_id', 'check_in', 'check_out',
                                                 'worked_hours', 'out_mode',
                                                 'create_date', 'write_date', 'in_ip_address', 'in_mode', 'in_browser',
                                                 'in_country_name', 'display_name']})

        for attendance in attendances:
            # Buscar o crear el empleado asociado
            employee_id = attendance['employee_id'] and attendance['employee_id'][1]  # Obtener el nombre del empleado
            employee = self._get_or_create_employee(employee_id) if employee_id else False

            vals = {
                'employee_id': employee.id if employee else False,
                'check_in': attendance['check_in'],
                'display_name': attendance['display_name'],
                'check_out': attendance['check_out'],
                'worked_hours': attendance['worked_hours'],
                'create_date': attendance['create_date'],
                'write_date': attendance['write_date'],
                'in_ip_address': attendance['in_ip_address'],
                'in_mode': attendance['in_mode'],
                'out_mode': attendance['out_mode'],
                'in_browser': attendance['in_browser'],
                'in_country_name': attendance['in_country_name'],
            }
            print(vals)
            _logger.info(vals)
            self._insert_direct('hr.attendance', vals)

        return True

    def transfer_data_employee(self):
        """Transferencia de registros de empleados (hr.employee) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de empleados (hr.employee)
        employee_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                      'hr.employee', 'search', [['|', ['active', '=', True], ['active', '=', False]]])
        employees = obj.execute_kw(self.source_db, uid, self.source_password,
                                   'hr.employee', 'read', [employee_ids],
                                   {'fields': ['id', 'name', 'work_email', 'mobile_phone', 'work_phone',
                                               'department_id', 'job_id', 'category_ids', 'gender', 'birthday',
                                               'country_id', 'create_date', 'write_date', 'active']})

        for employee in employees:
            # Buscar o crear el departamento asociado
            department_id = employee['department_id'] and employee['department_id'][
                1]  # Obtener el nombre del departamento
            department = self._get_or_create_department(department_id) if department_id else False

            # Buscar o crear el puesto de trabajo asociado
            job_id = employee['job_id'] and employee['job_id'][1]  # Obtener el nombre del puesto de trabajo
            job_position = self._get_or_create_job_position(job_id) if job_id else False

            # Obtener o crear etiquetas
            category_ids = False
            if employee['category_ids']:
                category_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'hr.employee.category', 'search_read',
                                              [[['id', 'in', employee['category_ids']]]], {'fields': ['name']})
                category_names = [cat['name'] for cat in category_ids] if category_ids else []
                category_ids = self._get_or_create_employee_categories(category_names)

            vals = {
                'name': employee['name'],
                'work_email': employee['work_email'],
                'mobile_phone': employee['mobile_phone'],
                'work_phone': employee['work_phone'],
                'department_id': department.id if department else False,
                'job_id': job_position.id if job_position else False,
                'category_ids': [(6, 0, category_ids)] if category_ids else False,
                # Many2many categorías (reemplazar todas las existentes)
                'gender': employee['gender'],
                'birthday': employee['birthday'],
                # 'address_home_id': employee['address_home_id'][0] if employee['address_home_id'] else False,
                'country_id': employee['country_id'][0] if employee['country_id'] else False,
                'create_date': employee['create_date'],
                'write_date': employee['write_date'],
                'active': employee['active'],
            }
            print(vals)
            _logger.info(vals)
            self._insert_if_not_exists_by_name('hr.employee', employee['name'], vals)

        return True

    def transfer_data_hr_leave_type(self):
        """Transferencia de registros de tipos de ausencias (hr.leave.type) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (hr.leave.type)
        hr_leave_type_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                           'hr.leave.type', 'search', [[]])
        hr_leave_types = obj.execute_kw(self.source_db, uid, self.source_password,
                                        'hr.leave.type', 'read', [hr_leave_type_ids],
                                        {'fields': [
                                            'id',
                                            'name',
                                            'leave_validation_type',
                                            # 'responsible_ids',
                                            'request_unit',
                                            'support_document',
                                            'time_type',
                                            'color',
                                            # 'icon_id',
                                            'requires_allocation',
                                            'employee_requests',
                                            'allocation_validation_type',
                                            'allows_negative',
                                        ]})

        for hr_leave_type in hr_leave_types:
            vals = {
                'name': hr_leave_type['name'],
                'leave_validation_type': hr_leave_type['leave_validation_type'],
                'request_unit': hr_leave_type['request_unit'],
                'support_document': hr_leave_type['support_document'],
                'time_type': hr_leave_type['time_type'],
                'color': hr_leave_type['color'],
                # 'icon_id': hr_leave_type['icon_id'][0] if hr_leave_type['icon_id'] else False,
                'requires_allocation': hr_leave_type['requires_allocation'],
                'employee_requests': hr_leave_type['employee_requests'],
                'allocation_validation_type': hr_leave_type['allocation_validation_type'],
                'allows_negative': hr_leave_type['allows_negative'],
            }
            print(vals)
            _logger.info(vals)
            self._insert_if_not_exists_by_name('hr.leave.type', hr_leave_type['name'], vals)

        return True

    def transfer_data_hr_leave(self):
        """Transferencia de registros de tipos de ausencias (hr.leave.type) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (hr.leave.type)
        hr_leave_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                      'hr.leave', 'search', [[]])
        hr_leaves = obj.execute_kw(self.source_db, uid, self.source_password,
                                   'hr.leave', 'read', [hr_leave_ids],
                                   {'fields': [
                                       'id',
                                       'name',
                                       'holiday_status_id',
                                       'employee_ids',
                                       'employee_id',
                                       'request_date_from',
                                       'request_date_to',
                                       'request_hour_from',
                                       'request_hour_to',
                                       'request_unit_half',
                                       'request_unit_hours',
                                       'request_date_from_period',
                                       'number_of_days_display',
                                       'active',
                                       'state',
                                   ]})

        for hr_leave in hr_leaves:
            # Buscar o crear el empleado asociado
            employee_ids = []
            if hr_leave['employee_ids']:
                employee_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'hr.employee', 'search_read', [[['id', 'in', hr_leave['employee_ids']]]],
                                              {'fields': ['name']})
                employee_names = [cat['name'] for cat in employee_ids] if employee_ids else []
                employee_ids = self._get_employees(employee_names)
            holiday_status_id = hr_leave['holiday_status_id'] and hr_leave['holiday_status_id'][
                1]  # Obtener el nombre del empleado
            holiday_status = self._get_or_create_holiday_status_id(holiday_status_id) if holiday_status_id else False
            print(hr_leave['id'])

            if employee_ids:
                vals = {
                    'name': hr_leave['name'],
                    'employee_id': employee_ids[0] if employee_ids else False,
                    'holiday_status_id': holiday_status.id if holiday_status else False,
                    'request_date_from': hr_leave['request_date_from'],
                    'request_date_to': hr_leave['request_date_to'],
                    'request_hour_from': hr_leave['request_hour_from'],
                    'request_hour_to': hr_leave['request_hour_to'],
                    'request_unit_half': hr_leave['request_unit_half'],
                    'request_unit_hours': hr_leave['request_unit_hours'],
                    'request_date_from_period': hr_leave['request_date_from_period'],
                    'number_of_days_display': hr_leave['number_of_days_display'],
                    'active': hr_leave['active'],
                    'state': hr_leave['state'],
                }
                print(vals)
                _logger.info(vals)
                self.env['hr.leave'].with_context(leave_skip_state_check=True, leave_skip_date_check=True).sudo().create(vals)

        return True

    def transfer_data_helpdesk_team(self):
        """Transferencia de registros de tipos de ausencias (helpdesk.team) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (helpdesk.team)
        helpdesk_team_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                           'helpdesk.team', 'search', [[]])
        helpdesk_teams = obj.execute_kw(self.source_db, uid, self.source_password,
                                        'helpdesk.team', 'read', [helpdesk_team_ids],
                                        {'fields': [
                                            'id',
                                            'name',
                                            'privacy_visibility',
                                            'use_alias',
                                            'alias_contact',
                                            'use_website_helpdesk_form',
                                            'use_helpdesk_timesheet',
                                            'allow_portal_ticket_closing',
                                            'use_rating',
                                        ]})

        for helpdesk_team in helpdesk_teams:
            vals = {
                'name': helpdesk_team['name'],
                'privacy_visibility': helpdesk_team['privacy_visibility'],
                'use_alias': helpdesk_team['use_alias'],
                'alias_contact': helpdesk_team['alias_contact'],
                'use_website_helpdesk_form': helpdesk_team['use_website_helpdesk_form'],
                'use_helpdesk_timesheet': helpdesk_team['use_helpdesk_timesheet'],
                'allow_portal_ticket_closing': helpdesk_team['allow_portal_ticket_closing'],
                'use_rating': helpdesk_team['use_rating'],
            }
            print(vals)
            _logger.info(vals)
            self._insert_if_not_exists_by_name('helpdesk.team', helpdesk_team['name'], vals)

        return True

    def transfer_data_helpdesk_stage(self):
        """Transferencia de registros de tipos de ausencias (helpdesk.stage) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (helpdesk.stage)
        helpdesk_stage_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                            'helpdesk.stage', 'search', [[]])
        helpdesk_stages = obj.execute_kw(self.source_db, uid, self.source_password,
                                         'helpdesk.stage', 'read', [helpdesk_stage_ids],
                                         {'fields': [
                                             'id',
                                             'name',
                                             'team_ids',
                                             'legend_normal',
                                             'legend_blocked',
                                             'legend_done',
                                         ]})

        for helpdesk_stage in helpdesk_stages:
            team_ids = []
            if helpdesk_stage['team_ids']:
                team_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                          'hr.employee', 'search_read', [[['id', 'in', helpdesk_stage['team_ids']]]],
                                          {'fields': ['name']})
                team_names = [cat['name'] for cat in team_ids] if team_ids else []
                team_ids = self._get_team_ids(team_names)

            vals = {
                'name': helpdesk_stage['name'],
                'team_ids': [(6, 0, team_ids)] if team_ids else False,
                'legend_normal': helpdesk_stage['legend_normal'],
                'legend_blocked': helpdesk_stage['legend_blocked'],
                'legend_done': helpdesk_stage['legend_done'],
            }
            print(vals)
            _logger.info(vals)
            self._insert_if_not_exists_by_name('helpdesk.stage', helpdesk_stage['name'], vals)

        return True

    def transfer_data_helpdesk_ticket(self):
        """Transferencia de registros de tipos de ausencias (helpdesk.ticket) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (helpdesk.ticket)
        helpdesk_ticket_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                             'helpdesk.ticket', 'search', [[]])
        helpdesk_tickets = obj.execute_kw(self.source_db, uid, self.source_password,
                                          'helpdesk.ticket', 'read', [helpdesk_ticket_ids],
                                          {'fields': [
                                              'id',
                                              'name',
                                              'team_id',
                                              'user_id',
                                              'priority',
                                              'tag_ids',
                                              'partner_id',
                                              'stage_id',
                                              'partner_phone',
                                              'email_cc',
                                              'description',
                                              'timesheet_ids',
                                              'message_ids',
                                          ]})

        for helpdesk_ticket in helpdesk_tickets:
            # Buscar o crear el departamento asociado
            team_id = helpdesk_ticket['team_id'] and helpdesk_ticket['team_id'][1]  # Obtener el nombre del departamento
            team = self._get_or_create_helpdesk_team(team_id) if team_id else False
            user_id = helpdesk_ticket['user_id'] and helpdesk_ticket['user_id'][1]  # Obtener el nombre del departamento
            user = self._get_or_create_user(user_id) if user_id else False
            partner_id = helpdesk_ticket['partner_id'] and helpdesk_ticket['partner_id'][
                1]  # Obtener el nombre del departamento
            partner = self._get_or_create_partner(partner_id) if partner_id else False
            stage_id = helpdesk_ticket['stage_id'] and helpdesk_ticket['stage_id'][
                1]  # Obtener el nombre del departamento
            stage = self._get_or_create_stage_id(stage_id) if stage_id else False

            tag_ids = []
            if helpdesk_ticket['tag_ids']:
                tag_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                         'helpdesk.tag', 'search_read', [[['id', 'in', helpdesk_ticket['tag_ids']]]],
                                         {'fields': ['name']})
                team_names = [cat['name'] for cat in tag_ids] if tag_ids else []
                tag_ids = self._get_helpdesk_tag_ids(team_names)

            vals = {
                'name': helpdesk_ticket['name'],
                'stage_id': stage.id if stage else False,
                'team_id': team.id if team else False,
                'user_id': user.id if user else False,
                'partner_id': partner.id if partner else False,
                'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
                'priority': helpdesk_ticket['priority'],
                'partner_phone': helpdesk_ticket['partner_phone'],
                'email_cc': helpdesk_ticket['email_cc'],
                'description': helpdesk_ticket['description'],
            }
            print(vals)
            _logger.info(vals)
            res = self._insert_direct('helpdesk.ticket', vals)
            self.transfer_message_ids(helpdesk_ticket['message_ids'], 'helpdesk.ticket', res.id)
            self.transfer_account_analytic_line(helpdesk_ticket['timesheet_ids'], helpdesk_ticket_id=res.id)

        return True

    def transfer_data_project_project(self):
        """Transferencia de registros de tipos de ausencias (project.project) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (project.project)
        project_project_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                             'project.project', 'search_read', [[]], {
                                                 'fields': [
                                                     'id',
                                                     'name',
                                                     'stage_id',  # project.project.stage
                                                     'partner_id',
                                                     'tag_ids',  # project.tags
                                                     'user_id',  # res.users
                                                     'label_tasks',
                                                     'date_start',
                                                     'allocated_hours',
                                                     'description',
                                                     'privacy_visibility',
                                                     'allow_task_dependencies',
                                                     'allow_milestones',
                                                     'allow_billable',
                                                     'allow_material',
                                                     'allow_timesheets',
                                                     'use_documents',
                                                     # 'documents_tag_ids', # documents.folder
                                                     'is_fsm',
                                                     'allow_worksheets',
                                                     'message_ids',
                                                 ]})

        for project_project in project_project_ids:
            user_id = project_project['user_id'] and project_project['user_id'][1]  # Obtener el nombre del departamento
            user = self._get_or_create_user(user_id) if user_id else False
            stage = self._get_or_create_many2one('project.project.stage', project_project['stage_id'],
                                                 ['name', 'fold']) if project_project['stage_id'] else False
            partner_id = project_project['partner_id'] and project_project['partner_id'][1]
            partner = self._get_or_create_partner(partner_id) if partner_id else False

            tag_ids = []
            if project_project['tag_ids']:
                tag_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                         'helpdesk.tag', 'search_read', [[['id', 'in', project_project['tag_ids']]]],
                                         {'fields': ['name']})
                tag_ids = self._get_m2m('helpdesk.tag', tag_ids, ['name', 'color'])
            if project_project['tag_ids']:
                tag_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                         'helpdesk.tag', 'search_read', [[['id', 'in', project_project['tag_ids']]]],
                                         {'fields': ['name']})
                tag_ids = self._get_m2m('helpdesk.tag', tag_ids, ['name', 'color'])

            vals = {
                'name': project_project['name'],
                'stage_id': stage.id if stage else False,
                'user_id': user.id if user else False,
                'partner_id': partner.id if partner else False,
                'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
                'label_tasks': project_project['label_tasks'],
                'date_start': project_project['date_start'],
                'allocated_hours': project_project['allocated_hours'],
                'description': project_project['description'],
                'privacy_visibility': project_project['privacy_visibility'],
                'allow_task_dependencies': project_project['allow_task_dependencies'],
                'allow_milestones': project_project['allow_milestones'],
                'allow_billable': project_project['allow_billable'],
                'allow_material': project_project['allow_material'],
                'allow_timesheets': project_project['allow_timesheets'],
                'use_documents': project_project['use_documents'],
                # 'documents_tag_ids': project_project['documents_tag_ids'],
                # 'is_fsm': project_project['is_fsm'],
                'allow_worksheets': project_project['allow_worksheets'],
            }
            print(vals)
            _logger.info(vals)
            res = self._insert_direct('project.project', vals)
            self.transfer_message_ids(project_project['message_ids'], 'project.project', res.id)

        return True

    def transfer_data_project_task(self):
        """Transferencia de registros de tipos de ausencias (project.project) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (project.project)
        project_project_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                             'project.project', 'search_read', [[]], {
                                                 'fields': [
                                                     'id',
                                                     'name',
                                                 ]})

        for project_project in project_project_ids:
            project_task_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'project.task', 'search_read',
                                              [[['project_id', '=', project_project['id']]]], {
                                                  'fields': [
                                                      'id',
                                                      'name',
                                                      'project_id',  # project.project
                                                      'partner_id',  # res.partner
                                                      'allocated_hours',
                                                      'user_ids',  # res.users
                                                      'tag_ids',  # res.users
                                                      'date_deadline',
                                                      'description',
                                                      'sequence',
                                                      'email_cc',
                                                      'date_assign',
                                                      'date_last_stage_update',
                                                      'message_ids',
                                                  ]})
            for project_task in project_task_ids:
                project = self._get_or_create_many2one('project.project', project_task['project_id']) if project_task[
                    'project_id'] else False
                partner = self._get_or_create_many2one('res.partner', project_task['partner_id']) if project_task[
                    'partner_id'] else False

                tag_ids = []
                if project_task['tag_ids']:
                    tag_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                             'project.tags', 'search_read', [[['id', 'in', project_task['tag_ids']]]],
                                             {'fields': ['name']})
                    tag_ids = self._get_m2m('project.tags', tag_ids, ['name', 'color'])

                user_ids = []
                if project_task['user_ids']:
                    user_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'res.users', 'search_read', [[['id', 'in', project_task['user_ids']]]],
                                              {'fields': ['name']})
                    user_ids = self._get_m2m('res.users', user_ids, ['name', 'login'])

                vals = {
                    'name': project_task['name'],
                    'project_id': project.id if project else False,
                    'partner_id': partner.id if partner else False,
                    'allocated_hours': project_task['allocated_hours'],
                    'user_ids': [(6, 0, user_ids)] if user_ids else False,
                    'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
                    'date_deadline': project_task['date_deadline'],
                    'description': project_task['description'],
                    'sequence': project_task['sequence'],
                    'email_cc': project_task['email_cc'],
                    'date_assign': project_task['date_assign'],
                    'date_last_stage_update': project_task['date_last_stage_update'],
                }
                print(vals)
                _logger.info(vals)
                res = self._insert_direct('project.task', vals)
                if project_task['message_ids']:
                    self.transfer_message_ids(project_task['message_ids'], 'project.task', res.id)
                self.transfer_account_analytic_line(project_project['timesheet_ids'], project_id=project.id, task_id=res.id)

        return True

    def transfer_data_product_templates(self):
        """Transferencia de registros de tipos de ausencias (product.template) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        self.transfer_data_uom()

        # Transferir registros de asistencia (product.template)
        product_template_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                              'product.template', 'search_read', [[]], {
                                                  'fields': [
                                                      'id',
                                                      'name',
                                                      'attribute_line_ids',  # product.template.stage
                                                      'list_price',
                                                      'default_code',
                                                      'sale_ok',
                                                      'purchase_ok',
                                                      'recurring_invoice',
                                                      'can_be_expensed',
                                                      'detailed_type',
                                                      'invoice_policy',
                                                      'product_tooltip',
                                                      'uom_id',  # uom.uom
                                                      'uom_po_id',  # uom.uom
                                                      'standard_price',
                                                      'categ_id',  # product.category
                                                      'barcode',
                                                      'product_tag_ids',  # product.tag m2m
                                                      'website_sequence',
                                                      'allow_out_of_stock_order',
                                                      'show_availability',
                                                      'responsible_id',  # res.users
                                                      'tracking',
                                                      'description',
                                                      'message_ids',
                                                  ]})

        for product_template in product_template_ids:
            responsible_id = product_template['responsible_id'] and product_template['responsible_id'][1]
            responsible_id = self._get_or_create_user(responsible_id) if responsible_id else False
            uom_id = self._get_or_create_many2one('uom.uom', product_template['uom_id']) if product_template[
                'uom_id'] else False
            uom_po_id = self._get_or_create_many2one('uom.uom', product_template['uom_po_id']) if product_template[
                'uom_po_id'] else False
            categ_id = self._get_or_create_many2one('product.category', product_template['categ_id']) if \
            product_template['categ_id'] else False

            product_tag_ids = []
            if product_template['product_tag_ids']:
                product_tag_ids = obj.execute_kw(self.source_db, uid, self.source_password,
                                                 'product.tag', 'search_read',
                                                 [[['id', 'in', product_template['product_tag_ids']]]],
                                                 {'fields': ['name']})
                product_tag_ids = self._get_m2m('product.tag', product_tag_ids, ['name', 'visible_on_ecommerce'])

            vals = {
                'name': product_template['name'],
                'list_price': product_template['list_price'],
                'default_code': product_template['default_code'],
                'sale_ok': product_template['sale_ok'],
                'purchase_ok': product_template['purchase_ok'],
                'recurring_invoice': product_template['recurring_invoice'],
                'can_be_expensed': product_template['can_be_expensed'],
                'detailed_type': product_template['detailed_type'],
                'invoice_policy': product_template['invoice_policy'],
                'product_tooltip': product_template['product_tooltip'],
                'uom_id': uom_id.id if uom_id else False,
                'uom_po_id': uom_po_id.id if uom_po_id else False,
                'standard_price': product_template['standard_price'],
                'categ_id': categ_id.id if categ_id else False,
                'barcode': product_template['barcode'],
                'product_tag_ids': [(6, 0, product_tag_ids)] if product_tag_ids else False,
                'website_sequence': product_template['website_sequence'],
                'allow_out_of_stock_order': product_template['allow_out_of_stock_order'],
                'show_availability': product_template['show_availability'],
                'responsible_id': responsible_id.id if responsible_id else False,
                'tracking': product_template['tracking'],
                'description': product_template['description'],
            }
            _logger.info(vals)
            res = self._insert_direct('product.template', vals)
            # Si el producto tiene atributos
            if product_template['attribute_line_ids']:
                attribute_lines = []
                for attribute_line in product_template['attribute_line_ids']:
                    # Obtener los atributos y sus valores desde la base de datos externa
                    attribute_vals = self.get_attribute_data(attribute_line)

                    # Crear o buscar los atributos y sus valores en la base de datos local
                    local_attribute = self.env['product.attribute'].search([('name', '=', attribute_vals['name'])],
                                                                           limit=1)
                    if not local_attribute:
                        local_attribute = self.env['product.attribute'].sudo().create({'name': attribute_vals['name']})

                    # Crear los valores de atributo si no existen
                    local_value = self.env['product.attribute.value'].search(
                        [('name', '=', attribute_vals['value_name']), ('attribute_id', '=', local_attribute.id)],
                        limit=1)
                    if not local_value:
                        local_value = self.env['product.attribute.value'].sudo().create({
                            'name': attribute_vals['value_name'],
                            'attribute_id': local_attribute.id
                        })

                    # Añadir la línea de atributos al producto
                    attribute_lines.append((0, 0, {
                        'attribute_id': local_attribute.id,
                        'value_ids': [(6, 0, [local_value.id])]
                    }))

                # Asignar las líneas de atributos al producto
                res.write({'attribute_line_ids': attribute_lines})

            self.transfer_message_ids(product_template['message_ids'], 'product.template', res.id)

        return True

    def get_attribute_data(self, attribute_line_id):
        uid = self._get_uid()
        _, obj = self._get_source_connection()
        attribute_line = obj.execute_kw(self.source_db, uid, self.source_password, 'product.template.attribute.line',
                                        'read', [[attribute_line_id]], {'fields': ['attribute_id', 'value_ids']})
        attribute = obj.execute_kw(self.source_db, uid, self.source_password, 'product.attribute', 'read',
                                   [[attribute_line[0]['attribute_id'][0]]], {'fields': ['name']})[0]
        value = obj.execute_kw(self.source_db, uid, self.source_password, 'product.attribute.value', 'read',
                               [[attribute_line[0]['value_ids'][0]]], {'fields': ['name']})[0]
        return {
            'name': attribute['name'],
            'value_name': value['name']
        }

    def transfer_data_uom(self):
        """Transferencia de registros de tipos de ausencias (helpdesk.team) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (helpdesk.team)
        uom_uom_ids = obj.execute_kw(self.source_db, uid, self.source_password, 'uom.uom', 'search_read', [[]], {
            'fields': [
                'id',
                'name',
                'category_id',  # uom.category
                'l10n_es_edi_facturae_uom_code',
                'uom_type',
                'factor',
                'active',
                'rounding',
            ]})

        for uom_uom in uom_uom_ids:
            category_id = self._get_or_create_many2one('uom.category', uom_uom['category_id']) if uom_uom[
                'category_id'] else False

            vals = {
                'name': uom_uom['name'],
                'category_id': category_id.id if category_id else False,
                'l10n_es_edi_facturae_uom_code': uom_uom['l10n_es_edi_facturae_uom_code'],
                'uom_type': uom_uom['uom_type'],
                'factor': uom_uom['factor'],
                'active': uom_uom['active'],
                'rounding': uom_uom['rounding'],
            }
            _logger.info(vals)
            self._insert_if_not_exists_by_name('uom.uom', uom_uom['name'], vals)

        return True

    def transfer_data_website(self):
        """Transferencia de registros de web (webiste) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()

        # Transferir registros de asistencia (helpdesk.stage)
        website_ids = obj.execute_kw(self.source_db, uid, self.source_password, 'website', 'search_read', [[]],
                                     {'fields': [
                                         'id',
                                         'name',
                                         'domain',
                                         'default_lang_id',
                                         'logo',
                                         'custom_code_head',
                                         'custom_code_footer',
                                         'favicon',
                                         'cookies_bar',
                                         'google_analytics_key',
                                         'google_maps_api_key',
                                         'google_search_console',
                                         'robots_txt',
                                         'social_facebook',
                                         'social_instagram',
                                         'social_linkedin',
                                         'social_twitter',
                                         'social_youtube',
                                     ]})

        for website in website_ids:
            vals = {
                'name': website['name'],
                'domain': website['name'],
                'default_lang_id': website['default_lang_id'][0],
                'language_ids': [(6, 0, [website['default_lang_id'][0]])] if website['default_lang_id'] else False,
                'logo': website['logo'],
                'custom_code_head': website['custom_code_head'],
                'custom_code_footer': website['custom_code_footer'],
                'favicon': website['favicon'],
                'cookies_bar': website['cookies_bar'],
                'google_analytics_key': website['google_analytics_key'],
                'google_maps_api_key': website['google_maps_api_key'],
                'google_search_console': website['google_search_console'],
                'robots_txt': website['robots_txt'],
                'social_facebook': website['social_facebook'],
                'social_instagram': website['social_instagram'],
                'social_linkedin': website['social_linkedin'],
                'social_twitter': website['social_twitter'],
                'social_youtube': website['social_youtube'],
            }
            _logger.info(vals)
            self._insert_if_not_exists_by_name('website', website['name'], vals)

        return True

    def transfer_data_website_pages(self):
        """Transferencia de registros de blog_post (blog.post) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()
        # Transferir registros de asistencia (helpdesk.stage)
        website_page_ids = obj.execute_kw(self.source_db, uid, self.source_password, 'website.page', 'search_read', [[]],
                                       {'fields': [
                                           'id',
                                           'active',
                                           'arch',
                                           'arch_base',
                                           'arch_db',
                                           'arch_fs',
                                           'arch_prev',
                                           'arch_updated',
                                           'can_publish',
                                           'create_date',
                                           'create_uid', # user.id
                                           'date_publish',
                                           'header_visible',
                                           'footer_visible',
                                           'is_homepage',
                                           'is_in_menu',
                                           'is_published',
                                           'is_seo_optimized',
                                           'is_visible',
                                           'key',
                                           'name',
                                           'priority',
                                           'seo_name',
                                           'track',
                                           'type',
                                           # 'url',
                                           'view_id', # ir.ui.view
                                           'visibility',
                                           'website_id',  # website
                                           'website_indexed',
                                           'website_meta_description',
                                           'website_meta_keywords',
                                           'website_meta_og_img',
                                           'website_meta_title',
                                           'website_published',
                                           'website_url',
                                           'write_date',
                                       ]})
        for website_page in website_page_ids:
            website_id = self._get_or_create_many2one('website', website_page['website_id']) if website_page['website_id'] else False
            create_uid = self._get_or_create_many2one('res.users', website_page['create_uid']) if website_page['create_uid'] else False
            view_id = self._get_or_create_many2one('ir.ui.view', website_page['view_id'], ['name', 'type', 'key', 'visibility', 'priority', 'active', 'track', 'mode', 'arch_db', 'arch_base']) if website_page['view_id'] else False
            vals = {
                'name': website_page['name'],
                'id': website_page['id'],
                'active': website_page['active'],
                'arch': website_page['arch'],
                'arch_base': website_page['arch_base'],
                'arch_db': website_page['arch_db'],
                'arch_fs': website_page['arch_fs'],
                'arch_prev': website_page['arch_prev'],
                'arch_updated': website_page['arch_updated'],
                'can_publish': website_page['can_publish'],
                'create_date': website_page['create_date'],
                'create_uid': create_uid.id if create_uid else False,
                'date_publish': website_page['date_publish'],
                'footer_visible': website_page['footer_visible'],
                'header_visible': website_page['header_visible'],
                'is_homepage': website_page['is_homepage'],
                'is_in_menu': website_page['is_in_menu'],
                'is_published': website_page['is_published'],
                'is_seo_optimized': website_page['is_seo_optimized'],
                'is_visible': website_page['is_visible'],
                'key': website_page['key'],
                'priority': website_page['priority'],
                'seo_name': website_page['seo_name'],
                'track': website_page['track'],
                'type': website_page['type'],
                'url': website_page['url'],
                'view_id': view_id.id if view_id else False,
                'visibility': website_page['visibility'],
                'website_id': website_id.id if website_id else False,
                'website_indexed': website_page['website_indexed'],
                'website_meta_description': website_page['website_meta_description'],
                'website_meta_keywords': website_page['website_meta_keywords'],
                'website_meta_og_img': website_page['website_meta_og_img'],
                'website_meta_title': website_page['website_meta_title'],
                'website_published': website_page['website_published'],
                # 'website_url': website_page['website_url'],
                'write_date': website_page['write_date'],
            }
            _logger.info(vals)
            self._insert_direct('website.page', vals)

        return True

    def transfer_data_blog_post(self):
        """Transferencia de registros de blog_post (blog.post) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()
        # Transferir registros de asistencia (helpdesk.stage)
        blog_blog_ids = obj.execute_kw(self.source_db, uid, self.source_password, 'blog.blog', 'search_read', [[]],
                                       {'fields': [
                                           'id',
                                           'name',
                                           'subtitle',
                                           'website_id',  # website
                                           'message_ids',
                                       ]})
        for blog in blog_blog_ids:
            website_id = self._get_or_create_many2one('website', blog['website_id']) if blog['website_id'] else False
            vals = {
                'name': blog['name'],
                'subtitle': blog['name'],
                'website_id': website_id.id if website_id else False,
            }
            _logger.info(vals)
            res = self._insert_if_not_exists_by_name('blog.blog', blog['name'], vals)
            self.transfer_message_ids(blog['message_ids'], 'blog.blog', res.id)


        # Transferir registros de asistencia (helpdesk.stage)
        blog_post_ids = obj.execute_kw(self.source_db, uid, self.source_password, 'blog.post', 'search_read', [[]],
                                     {'fields': [
                                         'id',
                                         'name',
                                         'active',
                                         'author_id', # res.partner
                                         'author_name',
                                         'blog_id', # blog.blog (name, website_id)
                                         'content',
                                         'cover_properties',
                                         'is_published',
                                         'post_date',
                                         'published_date',
                                         'seo_name',
                                         'subtitle',
                                         'teaser',
                                         'teaser_manual',
                                         'visits',
                                         'website_meta_description',
                                         'website_meta_keywords',
                                         'website_meta_og_img',
                                         'website_meta_title',
                                         'website_published',
                                         'website_url',
                                         'write_date',
                                         'write_uid', # res.users
                                         'message_ids',
                                     ]})

        for blog_post in blog_post_ids:
            author_id = self._get_or_create_many2one('res.partner', blog_post['author_id']) if blog_post['author_id'] else False
            blog_id = self._get_or_create_many2one('blog.blog', blog_post['blog_id']) if blog_post['blog_id'] else False
            write_uid = self._get_or_create_many2one('res.users', blog_post['write_uid']) if blog_post['write_uid'] else False
            vals = {
                'name': blog_post['name'],
                'active': blog_post['active'],
                'author_id': author_id.id if author_id else False,
                'blog_id': blog_id.id if blog_id else False,
                'write_uid': write_uid.id if write_uid else False,
                'author_name': blog_post['author_name'],
                'content': blog_post['content'],
                'cover_properties': blog_post['cover_properties'],
                'is_published': blog_post['is_published'],
                'post_date': blog_post['post_date'],
                'published_date': blog_post['published_date'],
                'seo_name': blog_post['seo_name'],
                'subtitle': blog_post['subtitle'],
                'teaser': blog_post['teaser'],
                'teaser_manual': blog_post['teaser_manual'],
                'visits': blog_post['visits'],
                'website_meta_description': blog_post['website_meta_description'],
                'website_meta_keywords': blog_post['website_meta_keywords'],
                'website_meta_og_img': blog_post['website_meta_og_img'],
                'website_meta_title': blog_post['website_meta_title'],
                'website_published': blog_post['website_published'],
                'website_url': blog_post['website_url'],
                'write_date': blog_post['write_date'],
            }
            _logger.info(vals)
            res = self._insert_if_not_exists_by_name('blog.post', blog_post['name'], vals)
            self.transfer_message_ids(blog_post['message_ids'], 'blog.post', res.id)
        return True

    def transfer_message_ids(self, message_ids, model, res_id):
        """Transferencia de registros de tipos de ausencias (helpdesk.ticket) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()
        messages = obj.execute_kw(self.source_db, uid, self.source_password,
                                  'mail.message', 'read', [message_ids],
                                  {'fields': [
                                      'id',
                                      'subject',
                                      'date',
                                      'email_from',
                                      'author_id',  # res.partner
                                      'message_type',
                                      'subtype_id',  # mail.message.subtype
                                      'is_internal',
                                      # 'model',
                                      # 'res_id',
                                      'record_name',
                                      # 'parent_id', # mail.message
                                      'reply_to',
                                      'reply_to_force_new',
                                      'message_id',
                                      'body',
                                      'attachment_ids',
                                  ]})

        for message in messages:
            # Buscar o crear el departamento asociado
            author_id = message['author_id'] and message['author_id'][1]  # Obtener el nombre del departamento
            author = self._get_or_create_partner(author_id) if author_id else False
            # subtype_id = message['subtype_id'] and message['subtype_id'][1]  # Obtener el nombre del departamento
            # vals = ['name', 'default', 'res_model']
            subtype = self._get_or_create_many2one('mail.message.subtype', message['subtype_id'],
                                                   ['name', 'default', 'res_model']) if message['subtype_id'] else False

            vals = {
                'author_id': author.id if author else False,
                'subtype_id': subtype.id if subtype else False,
                'subject': message['subject'],
                'date': message['date'],
                'email_from': message['email_from'],
                'message_type': message['message_type'],
                'is_internal': message['is_internal'],
                'model': model,
                'res_id': res_id,
                'record_name': message['record_name'],
                'reply_to': message['reply_to'],
                'reply_to_force_new': message['reply_to_force_new'],
                'message_id': message['message_id'],
                'body': message['body'],
            }
            _logger.info(vals)
            new_message_id = self._insert_direct('mail.message', vals)
            if new_message_id and message['attachment_ids']:
                message_attachments = []
                attachments = obj.execute_kw(self.source_db, uid, self.source_password, 'ir.attachment', 'read',
                                             [message['attachment_ids']], {'fields': ['datas', 'name', 'mimetype']})
                for attachment in attachments:
                    attachment_data = {
                        'name': attachment['name'],
                        'datas': attachment['datas'],  # El archivo en base64
                        'res_model': model,  # El modelo del registro destino
                        'res_id': res_id,  # El ID del registro en la segunda base de datos
                        'mimetype': attachment['mimetype'],
                    }
                    new_attachment_id = self.env['ir.attachment'].sudo().create(attachment_data)
                    message_attachments.append(new_attachment_id.id)
                if message_attachments:
                    new_message_id.attachment_ids = [(6, 0, message_attachments)]
        return True

    def transfer_account_analytic_line(self, account_analytic_line_ids, project_id=False, task_id=False, helpdesk_ticket_id=False):
        """Transferencia de registros de tipos de ausencias (account.analytic.line) entre bases de datos."""
        uid = self._get_uid()
        _, obj = self._get_source_connection()
        account_analytic_lines = obj.execute_kw(self.source_db, uid, self.source_password, 'account.analytic.line',
                                                'read', [account_analytic_line_ids],  {
                                                    'fields': [
                                                        'id',
                                                        'date',
                                                        'name',
                                                        'employee_id',
                                                        'project_id',
                                                        'task_id',
                                                        'helpdesk_ticket_id',
                                                        'unit_amount',
                                                    ]})

        for account_analytic_line in account_analytic_lines:
            employee_id = self._get_or_create_many2one('hr.employee', account_analytic_line['employee_id']) if account_analytic_line['employee_id'] else False
            vals = {
                'employee_id': employee_id.id if employee_id else False,
                'project_id': project_id,
                'task_id': task_id,
                'helpdesk_ticket_id': helpdesk_ticket_id,
                'date': account_analytic_line['date'],
                'unit_amount': account_analytic_line['unit_amount'],
                'name': account_analytic_line['name'],
            }
            _logger.info(vals)
            self._insert_direct('account.analytic.line', vals)
        return True
