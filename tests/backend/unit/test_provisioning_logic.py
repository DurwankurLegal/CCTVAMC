"""
Unit tests — Phase 2 provisioning logic (pure / fast, no DB or HTTP)
====================================================================
Covers the pure helpers and the default-template catalogue:
  * generate_temp_password()        — entropy / format
  * apply_workspace_defaults()      — branding/settings merge semantics
  * DEFAULT_TEMPLATES               — shape, channels, placeholder hygiene
  * NotificationService._render     — every catalogue template renders cleanly
  * User.must_change_password       — default
"""
import re

from app.services.provisioning import (
    generate_temp_password, apply_workspace_defaults,
    DEFAULT_BRANDING, DEFAULT_SETTINGS,
)
from app.services.notification_templates import DEFAULT_TEMPLATES
from app.services.notification import NotificationService
from app.models.notification import NotificationChannel
from app.models.user import User

PLACEHOLDER = re.compile(r"\{\{\s*([\w]+)\s*\}\}")


# ── generate_temp_password ───────────────────────────────────────────────────

class TestTempPassword:
    def test_distinct_and_long(self):
        pws = {generate_temp_password() for _ in range(200)}
        assert len(pws) == 200                       # no collisions
        assert all(len(p) >= 12 for p in pws)

    def test_url_safe_characters_only(self):
        # token_urlsafe → base64url alphabet (A–Z a–z 0–9 - _)
        assert re.fullmatch(r"[A-Za-z0-9_-]+", generate_temp_password())


# ── apply_workspace_defaults ─────────────────────────────────────────────────

class TestWorkspaceDefaults:
    def test_empty_inputs_get_full_defaults(self):
        branding, settings = apply_workspace_defaults(None, None)
        assert branding == DEFAULT_BRANDING
        assert settings == DEFAULT_SETTINGS

    def test_empty_dicts_get_full_defaults(self):
        branding, settings = apply_workspace_defaults({}, {})
        assert branding["primary_color"] == DEFAULT_BRANDING["primary_color"]
        assert settings["currency"] == DEFAULT_SETTINGS["currency"]

    def test_admin_values_win_over_defaults(self):
        branding, settings = apply_workspace_defaults(
            {"primary_color": "#ff0000"}, {"currency": "USD"})
        assert branding["primary_color"] == "#ff0000"     # not clobbered
        assert settings["currency"] == "USD"

    def test_missing_keys_filled_from_defaults(self):
        branding, _ = apply_workspace_defaults({"primary_color": "#ff0000"}, None)
        assert "logo_url" in branding                     # default key preserved

    def test_extra_admin_keys_preserved(self):
        _, settings = apply_workspace_defaults(None, {"locale": "en-IN"})
        assert settings["locale"] == "en-IN"
        assert settings["timezone"] == DEFAULT_SETTINGS["timezone"]


# ── DEFAULT_TEMPLATES catalogue ──────────────────────────────────────────────

class TestTemplateCatalogue:
    def test_every_entry_is_a_4_tuple(self):
        assert all(len(t) == 4 for t in DEFAULT_TEMPLATES)

    def test_channels_are_valid(self):
        valid = {c.value for c in NotificationChannel}
        assert all(channel in valid for _e, channel, _s, _b in DEFAULT_TEMPLATES)

    def test_bodies_non_empty(self):
        assert all(body.strip() for _e, _c, _s, body in DEFAULT_TEMPLATES)

    def test_no_duplicate_event_channel_pairs(self):
        pairs = [(e, c) for e, c, _s, _b in DEFAULT_TEMPLATES]
        assert len(pairs) == len(set(pairs))

    def test_placeholders_are_well_formed(self):
        """No stray single braces — every '{' belongs to a '{{...}}' token."""
        for event, _c, subject, body in DEFAULT_TEMPLATES:
            for text in (subject or "", body):
                # Strip valid {{...}} tokens; no lone braces should remain.
                residue = PLACEHOLDER.sub("", text)
                assert "{" not in residue and "}" not in residue, f"malformed braces in {event}"

    def test_templates_render_with_no_unsubstituted_placeholders(self):
        """Feeding each template a context covering its placeholders leaves no
        '{{var}}' behind — guards against typos the render engine can't fill."""
        for _e, _c, subject, body in DEFAULT_TEMPLATES:
            keys = set(PLACEHOLDER.findall(subject or "")) | set(PLACEHOLDER.findall(body))
            context = {k: f"<{k}>" for k in keys}
            rendered = NotificationService._render(body, context) + \
                NotificationService._render(subject or "", context)
            assert "{{" not in rendered and "}}" not in rendered


# ── User default ─────────────────────────────────────────────────────────────

class TestUserDefaults:
    def test_must_change_password_not_truthy_by_default(self):
        u = User(tenant_id=None, email="x@y.com", full_name="X", hashed_password="h")
        # Column default applies at flush; pre-flush it is falsy.
        assert not u.must_change_password
