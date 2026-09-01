# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class IetCleanupRule(models.Model):
    _name = 'iet.cleanup.rule'
    _description = 'Import/Export Toolkit - Data Cleanup Rule'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    model_name = fields.Char(string='Model', required=True, help='Technical name of the model to clean up.')
    cleanup_type = fields.Selection(
        selection=[
            ('trim_whitespace', 'Trim Whitespace'),
            ('remove_duplicates', 'Remove Duplicates'),
            ('fix_case', 'Fix Case'),
            ('validate_email', 'Validate Email'),
            ('normalize_phone', 'Normalize Phone'),
            ('fill_defaults', 'Fill Defaults'),
        ],
        string='Cleanup Type',
        required=True,
        tracking=True,
    )
    field_name = fields.Char(string='Field Name', help='Name of the field to clean up.')
    is_active = fields.Boolean(string='Active', default=True)
    last_run = fields.Datetime(string='Last Run', readonly=True)
    records_cleaned = fields.Integer(string='Records Cleaned', readonly=True)

    def action_run_cleanup(self):
        """Execute the cleanup rule against the target model."""
        self.ensure_one()
        if not self.model_name or not self.field_name:
            raise UserError('Model and field name are required to run a cleanup rule.')
        model = self.env[self.model_name]
        if self.field_name not in model._fields:
            raise UserError('Field "%s" does not exist on model "%s".' % (self.field_name, self.model_name))
        field_meta = model._fields[self.field_name]
        if field_meta.type not in ('char', 'text', 'html'):
            if self.cleanup_type in ('trim_whitespace', 'fix_case', 'validate_email', 'normalize_phone'):
                raise UserError('Cleanup type "%s" requires a text-based field.' % self.cleanup_type)

        records = model.search([(self.field_name, '!=', False)])
        cleaned = 0

        if self.cleanup_type == 'trim_whitespace':
            for rec in records:
                val = rec[self.field_name]
                if isinstance(val, str):
                    new_val = val.strip()
                    if new_val != val:
                        rec[self.field_name] = new_val
                        cleaned += 1

        elif self.cleanup_type == 'remove_duplicates':
            seen = set()
            to_unlink = []
            for rec in records:
                val = rec[self.field_name]
                key = val.strip().lower() if isinstance(val, str) else val
                if key in seen:
                    to_unlink.append(rec.id)
                else:
                    seen.add(key)
            if to_unlink:
                model.browse(to_unlink).unlink()
                cleaned = len(to_unlink)

        elif self.cleanup_type == 'fix_case':
            for rec in records:
                val = rec[self.field_name]
                if isinstance(val, str) and val:
                    new_val = val.strip().capitalize()
                    if new_val != val:
                        rec[self.field_name] = new_val
                        cleaned += 1

        elif self.cleanup_type == 'validate_email':
            email_re = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
            for rec in records:
                val = rec[self.field_name]
                if isinstance(val, str) and val and not email_re.match(val.strip()):
                    rec[self.field_name] = False
                    cleaned += 1

        elif self.cleanup_type == 'normalize_phone':
            for rec in records:
                val = rec[self.field_name]
                if isinstance(val, str) and val:
                    digits = re.sub(r'\D', '', val)
                    new_val = '+%s' % digits if digits else False
                    if new_val != val:
                        rec[self.field_name] = new_val
                        cleaned += 1

        elif self.cleanup_type == 'fill_defaults':
            default_val = field_meta.default(self.env[model._name])
            for rec in records:
                val = rec[self.field_name]
                if not val and default_val is not None:
                    rec[self.field_name] = default_val
                    cleaned += 1

        self.write({
            'last_run': fields.Datetime.now(),
            'records_cleaned': cleaned,
        })

    @api.model
    def action_run_active_rules(self):
        """Run all active cleanup rules - can be called from cron."""
        for rule in self.search([('is_active', '=', True)]):
            try:
                rule.action_run_cleanup()
            except Exception:
                pass
