# -*- coding: utf-8 -*-
import base64
import io
import json
import csv

from odoo import api, fields, models
from odoo.exceptions import UserError


class IetImportJob(models.Model):
    _name = 'iet.import.job'
    _description = 'Import/Export Toolkit - Import Job'
    _order = 'created_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Job Name', required=True, tracking=True)
    model_name = fields.Char(string='Model', required=True, help='Technical name of the model to import into.')
    file_name = fields.Char(string='File Name')
    file_data = fields.Binary(string='Import File', required=True, attachment=True)
    mapping_config = fields.Text(
        string='Field Mapping (JSON)',
        help='JSON mapping of source columns to target fields, e.g. {"Name": "name", "Email": "email"}.',
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
    imported_count = fields.Integer(string='Imported', readonly=True)
    skipped_count = fields.Integer(string='Skipped', readonly=True)
    error_count = fields.Integer(string='Errors', readonly=True)
    error_log = fields.Text(string='Error Log', readonly=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now, readonly=True)

    def action_run_import(self):
        """Execute the import job from the uploaded file."""
        self.ensure_one()
        self.state = 'running'
        self.imported_count = 0
        self.skipped_count = 0
        self.error_count = 0
        error_lines = []
        try:
            if not self.file_data:
                raise UserError('No file to import.')
            model = self.env[self.model_name]
            mapping = {}
            if self.mapping_config:
                mapping = json.loads(self.mapping_config)

            raw = base64.b64decode(self.file_data)
            content = raw.decode('utf-8')

            if self.file_name and self.file_name.lower().endswith('.csv'):
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
            elif self.file_name and self.file_name.lower().endswith('.json'):
                rows = json.loads(content)
                if isinstance(rows, dict):
                    rows = [rows]
            else:
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)

            for idx, row in enumerate(rows, start=1):
                try:
                    vals = {}
                    for source_col, target_field in mapping.items():
                        if source_col in row:
                            vals[target_field] = row[source_col]
                    if not vals:
                        if mapping:
                            vals = {v: row.get(k) for k, v in mapping.items() if k in row}
                        else:
                            vals = {k: v for k, v in row.items() if k in model._fields}
                    if not vals:
                        self.skipped_count += 1
                        continue
                    model.create(vals)
                    self.imported_count += 1
                except Exception as e:
                    self.error_count += 1
                    error_lines.append('Row %s: %s' % (idx, str(e)))

            self.error_log = '\n'.join(error_lines) if error_lines else False
            self.state = 'done'
        except Exception as e:
            self.state = 'failed'
            self.error_log = str(e)
            raise UserError('Import failed: %s' % str(e))

    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({
            'state': 'draft',
            'imported_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'error_log': False,
        })
