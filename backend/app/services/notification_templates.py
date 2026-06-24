"""Default per-tenant notification templates seeded at provisioning time.

Tenants get branded, editable templates instead of the generic fallback in
``NotificationService`` (which still covers any event without a template). The
``{{var}}`` placeholders must match the ``context=`` dicts the call sites pass to
``NotificationService.send()`` (see app/workers/tasks.py and the services).
"""
from app.models.notification import NotificationChannel
from app.services import notification_events as ev


# (event_type, channel, subject, body)
DEFAULT_TEMPLATES = [
    (ev.AMC_EXPIRY, NotificationChannel.EMAIL.value,
     "Your AMC {{contract_number}} expires in {{days}} days",
     "Dear customer,\n\nYour AMC contract {{contract_number}} is due to expire on "
     "{{end_date}} ({{days}} days from now). Please contact us to renew and avoid "
     "any interruption in service.\n\nThank you."),

    (ev.PAYMENT_DUE, NotificationChannel.EMAIL.value,
     "Invoice {{invoice_number}} — payment due",
     "Dear customer,\n\nInvoice {{invoice_number}} for an amount of "
     "{{amount_due}} is due on {{due_date}}. Kindly arrange the payment at your "
     "earliest convenience.\n\nThank you."),

    (ev.WARRANTY_EXPIRY, NotificationChannel.EMAIL.value,
     "Warranty expiring for {{asset_name}}",
     "The manufacturer warranty for {{asset_name}} is expiring on {{expiry_date}}. "
     "Consider an AMC to keep your equipment covered."),

    (ev.SLA_BREACH, NotificationChannel.IN_APP.value,
     "Ticket {{ticket_number}} has breached SLA",
     "Service ticket {{ticket_number}} (priority {{priority}}) has breached its "
     "SLA deadline and needs immediate attention."),

    (ev.TICKET_ASSIGNED, NotificationChannel.IN_APP.value,
     "New ticket assigned: {{ticket_number}}",
     "Service ticket {{ticket_number}} ({{priority}}) has been assigned to you."),

    (ev.VISIT_REMINDER, NotificationChannel.EMAIL.value,
     "Upcoming service visit on {{visit_date}}",
     "This is a reminder of your scheduled service visit on {{visit_date}}."),

    (ev.INSTALLATION_HANDOVER, NotificationChannel.EMAIL.value,
     "Installation handover — {{site_name}}",
     "Your CCTV installation at {{site_name}} has been handed over. An AMC has been "
     "activated and warranties registered."),

    (ev.LEAD_FOLLOWUP, NotificationChannel.IN_APP.value,
     "Follow up with lead {{name}}",
     "Reminder to follow up with lead {{name}} ({{phone}})."),

    (ev.QUOTE_SENT, NotificationChannel.EMAIL.value,
     "Quotation {{quotation_number}}",
     "Please find your quotation {{quotation_number}} for {{total_amount}}. It is "
     "valid until {{valid_until}}."),

    (ev.LOW_STOCK, NotificationChannel.IN_APP.value,
     "Low stock: {{item_name}}",
     "Stock for {{item_name}} is low ({{quantity}} remaining). Consider reordering."),
]
