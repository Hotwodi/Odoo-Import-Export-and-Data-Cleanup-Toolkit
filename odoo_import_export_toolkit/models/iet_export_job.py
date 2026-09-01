# -*- coding: utf-8 -*-
import base64
import io
import json
import csv

from odoo import api, fields, models
from odoo.exceptions import UserError


class IetExportJob(models.Model):
    _name = 'iet.export.job'
    _description = 'Import/Export Toolkit - Export Job'
    _order = 'created_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Job Name', required=True, tracking=True)
    model_name = fields.Char(string='Model', required=True, help='Technical name of the model to export.')
    export_format = fields.Selection(
        selection=[
            ('csv', 'CSV'),
            ('xlsx', 'XLSX'),
            ('json', 'JSON'),
        ],
        string='Export Format',
        default='csv',
        required=True,
    )
    field_list = fields.Text(
        string='Fields to Export',
        help='Comma-separated list of field names to export.',
    )
    filter_domain = fields.Text(
        string='Filter Domain',
        help='Odoo domain expression to filter records, e.g. [("active", "=", True)].',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    file_data = fields.Binary(string='Exported File', readonly=True, attachment=True)
    file_name = fields.Char(string='File Name', readonly=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now, readonly=True)
    record_count = fields.Integer(string='Record Count', readonly=True)

    def action_run_export(self):
        """Execute the export job and generate the output file."""
        self.ensure_one()
        self.state = 'running'
        try:
            model = self.env[self.model_name]
            domain = []
            if self.filter_domain:
                domain = eval(self.filter_domain)  # noqa: S307 - admin tool
            records = model.search(domain)
            fields_to_export = []
            if self.field_list:
                fields_to_export = [f.strip() for f in self.field_list.split(',') if f.strip()]
            if not fields_to_export:
                fields_to_export = list(model._fields.keys())

            self.record_count = len(records)

            if self.export_format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(fields_to_export)
                for rec in records:
                    writer.writerow([self._format_field_value(rec, f) for f in fields_to_export])
                file_content = output.getvalue().encode('utf-8')
                file_name = '%s_export.csv' % self.model_name
            elif self.export_format == 'json':
                data = []
                for rec in records:
                    row = {}
                    for f in fields_to_export:
                        row[f] = self._format_field_value(rec, f, for_json=True)
                    data.append(row)
                file_content = json.dumps(data, indent=2, default=str).encode('utf-8')
                file_name = '%s_export.json' % self.model_name
            elif self.export_format == 'xlsx':
                try:
                    import openpyxl
                except ImportError:
                    raise UserError('The openpyxl library is required for XLSX export. Please install it.')
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = 'Export'
                ws.append(fields_to_export)
                for rec in records:
                    ws.append([self._format_field_value(rec, f) for f in fields_to_export])
                buf = io.BytesIO()
                wb.save(buf)
                file_content = buf.getvalue()
                file_name = '%s_export.xlsx' % self.model_name
            else:
                raise UserError('Unsupported export format: %s' % self.export_format)

            self.write({
                'file_data': base64.b64encode(file_content),
                'file_name': file_name,
                'state': 'done',
            })
        except Exception as e:
            self.state = 'failed'
            raise UserError('Export failed: %s' % str(e))

    @api.model
    def _format_field_value(self, record, field_name, for_json=False):
        """Format a field value for export output."""
        if field_name not in record._fields:
            return ''
        value = record[field_name]
        if isinstance(value, models.Model):
            return value.display_name if value else ''
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return value[1] if not for_json else value[1]
        return value if value is not None else ''

    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'file_data': False,
            'file_name': False,
            'record_count': 0,
        })
