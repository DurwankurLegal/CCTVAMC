"""Event catalogue for the notification engine (see TAD section 9.2).

These constants are the ``event_type`` keys used both when calling
``NotificationService.send()`` and when defining templates per tenant.
"""

LEAD_FOLLOWUP = "lead_followup"
QUOTE_SENT = "quote_sent"
TICKET_ASSIGNED = "ticket_assigned"
TICKET_UPDATED = "ticket_updated"
SLA_BREACH = "sla_breach"
VISIT_REMINDER = "visit_reminder"
AMC_EXPIRY = "amc_expiry"
PAYMENT_DUE = "payment_due"
WARRANTY_EXPIRY = "warranty_expiry"
INSTALLATION_HANDOVER = "installation_handover"

ALL_EVENTS = [
    LEAD_FOLLOWUP, QUOTE_SENT, TICKET_ASSIGNED, TICKET_UPDATED, SLA_BREACH,
    VISIT_REMINDER, AMC_EXPIRY, PAYMENT_DUE, WARRANTY_EXPIRY, INSTALLATION_HANDOVER,
]
