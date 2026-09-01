# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class IetDataValidation(models.Model):
    _name = 'iet.data.validation'
    _description = 'Import/Export Toolkit - Data Validation Result'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Validation Name', required=True, tracking=True)
    model_name = fields.Char(string='Model', required=True, help='Technical name of the model being validated.')
    field_name = fields.Char(string='Field Name', required=True)
    validation_type = fields.Selection(
        selection=[
            ('required', 'Required'),
            ('format', 'Format'),
            ('range', 'Range'),
            ('unique', 'Unique'),
            ('reference', 'Reference'),
        ],
        string='Validation Type',
        required=True,
        tracking=True,
    )
    invalid_count = fields.Integer(string='Invalid Records', readonly=True)
    total_count = fields.Integer(string='Total Records', readonly=True)
    ai_suggestions = fields.Text(string='AI Suggestions', readonly=True)
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('fixed', 'Fixed'),
            ('ignored', 'Ignored'),
        ],
        string='Status',
        default='pending',
        required=True,
        tracking=True,
    )

    def action_run_validation(self):
        """Run validation against the target model/field and populate results."""
        for record in self:
            if not record.model_name or not record.field_name:
                continue
            model = self.env[record.model_name]
            if record.field_name not in model._fields:
                continue
            all_records = model.search([])
            record.total_count = len(all_records)
            invalid_ids = []

            if record.validation_type == 'required':
                invalid_ids = all_records.filtered(lambda r: not r[record.field_name]).ids
            elif record.validation_type == 'unique':
                seen = {}
                for rec in all_records:
                    val = rec[record.field_name]
                    if val in seen:
                        invalid_ids.append(rec.id)
                        if seen[val] not in invalid_ids:
                            invalid_ids.append(seen[val])
                    else:
                        seen[val] = rec.id
            elif record.validation_type == 'format':
                email_re = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
                field_meta = model._fields[record.field_name]
                if field_meta.type in ('char', 'text'):
                    invalid_ids = all_records.filtered(
                        lambda r: r[record.field_name] and not email_re.match(str(r[record.field_name]).strip())
                    ).ids
            elif record.validation_type == 'range':
                field_meta = model._fields[record.field_name]
                if field_meta.type in ('integer', 'float'):
                    invalid_ids = all_records.filtered(lambda r: r[record.field_name] is not None and r[record.field_name] < 0).ids
            elif record.validation_type == 'reference':
                field_meta = model._fields[record.field_name]
                if field_meta.type in ('many2one',):
                    invalid_ids = all_records.filtered(lambda r: r[record.field_name] and not r[record.field_name].exists()).ids

            record.invalid_count = len(invalid_ids)
            record.ai_suggestions = record._generate_ai_suggestions(invalid_ids)
            record.state = 'pending'

    def _generate_ai_suggestions(self, invalid_ids):
        """Generate AI-style suggestions for fixing invalid records."""
        if not invalid_ids:
            return 'No invalid records found. All records pass validation.'
        suggestions = []
        suggestions.append('Found %s invalid record(s) for field "%s" on model "%s".' % (
            len(invalid_ids), self.field_name, self.model_name))
        if self.validation_type == 'required':
            suggestions.append('Suggestion: Populate the "%s" field for all records, or set a sensible default value.' % self.field_name)
        elif self.validation_type == 'unique':
            suggestions.append('Suggestion: Review and merge or archive duplicate records. Consider adding a unique constraint on "%s".' % self.field_name)
        elif self.validation_type == 'format':
            suggestions.append('Suggestion: Standardize the format of "%s" (e.g. valid email pattern). Use a cleanup rule to fix invalid entries.' % self.field_name)
        elif self.validation_type == 'range':
            suggestions.append('Suggestion: Correct out-of-range values in "%s". Consider adding a range constraint.' % self.field_name)
        elif self.validation_type == 'reference':
            suggestions.append('Suggestion: Fix or clear broken references in "%s". Some linked records may have been deleted.' % self.field_name)
        return '\n'.join(suggestions)

    def action_mark_fixed(self):
        self.write({'state': 'fixed'})

    def action_mark_ignored(self):
        self.write({'state': 'ignored'})
