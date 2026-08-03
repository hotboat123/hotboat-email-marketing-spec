# Transport layer for outgoing mail — send_email() is the single funnel (Resend or SES).
# Content/policy helpers (footer injection, unsubscribe headers, name formatting) stay in
# app.services.email_sender — this package is transport only.
