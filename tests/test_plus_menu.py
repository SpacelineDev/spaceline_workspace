from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


class PlusMenuTests(unittest.TestCase):

    def test_provider_connections_require_explicit_selection_and_never_round_robin(self):
        self.assertIn('data-profile-enabled="${escapeHTML(p.id)}"', APP_JS)
        self.assertIn('data-profile-enabled', APP_JS)
        self.assertIn('set_profile_enabled', (Path(__file__).parents[1] / "app" / "workspace.py").read_text(encoding="utf-8"))
        main_source = (Path(__file__).parents[1] / "app" / "main.py").read_text(encoding="utf-8")
        pool = main_source[main_source.index("def connection_pool_order("):main_source.index("def discover_profile_model_catalog(")]
        self.assertIn("never choose a fallback model", pool)
        self.assertIn("return [selected]", pool)
        self.assertNotIn("round-robin", pool.lower())

    def test_model_picker_exposes_live_catalog_pricing_and_free_filter(self):
        self.assertIn('catalog', APP_JS)
        self.assertIn('data-model-filter="free"', APP_JS)
        self.assertIn('modelPriceFilter', APP_JS)
        self.assertIn('zero-priced-may-require-credits', (Path(__file__).parents[1] / "app" / "ai_provider.py").read_text(encoding="utf-8"))

    def test_image_studio_supports_openai_gemini_and_edenai_image_connections(self):
        self.assertIn("profile.provider === 'gemini'", APP_JS)
        self.assertIn("gemini-3.1-flash-image", APP_JS)
        self.assertIn("/interactions", (Path(__file__).parents[1] / "app" / "ai_provider.py").read_text(encoding="utf-8"))
        self.assertIn("edenai", APP_JS)
        self.assertIn("/api/images/models/", APP_JS)

    def test_image_generation_action_and_model_usage_meter_are_present(self):
        self.assertIn('data-tool-action="image_generate"', APP_JS)
        self.assertIn('id="modelUsageButton"', APP_JS)
        self.assertIn('id="modelUsagePanel"', APP_JS)
        self.assertIn('function refreshModelUsage()', APP_JS)

    def test_api_key_vault_has_individual_test_connection_action(self):
        self.assertIn('data-key-test="${escapeHTML(k.id)}"', APP_JS)
        self.assertIn("/api/keys/${encodeURIComponent(keyId)}/test", APP_JS)
        self.assertIn("keyTestResults", APP_JS)
        self.assertIn("Test connection", APP_JS)

    def test_browser_panel_is_presented_as_embedded_not_external_chrome(self):
        self.assertIn("Spaceline embedded browser", APP_JS)
        self.assertIn("headless=True", (Path(__file__).parents[1] / "app" / "browser.py").read_text(encoding="utf-8"))

    def test_workbench_starts_collapsed_and_opens_for_active_work(self):
        self.assertIn("workbenchCollapsed: true", APP_JS)
        self.assertIn("function openWorkbenchForTask", APP_JS)

    def test_chat_composer_exposes_a_plus_tools_menu(self):
        self.assertIn('id="openToolsMenu"', APP_JS)
        self.assertIn('id="toolsMenu"', APP_JS)
        self.assertIn('aria-expanded=', APP_JS)

    def test_plus_menu_offers_modes_browser_skills_and_connectors(self):
        for token in (
            "web_search", "deep_think", "deep_research",
            'data-tool-action="browser"',
            'data-tool-action="skills"',
            'data-tool-action="connectors"',
        ):
            self.assertIn(token, APP_JS)

    def test_plus_menu_supports_local_text_file_attachments(self):
        self.assertIn('id="composerFileInput"', APP_JS)
        self.assertIn("state.attachments", APP_JS)
        self.assertIn("file.text()", APP_JS)
        self.assertIn("Attached file:", APP_JS)
        self.assertIn("250 * 1024", APP_JS)  # Text-only attachments are bounded.
        self.assertIn("20 * 1024 * 1024", APP_JS)  # Office/PDF extraction uses a separate bounded upload path.
        self.assertIn("/api/files/analyze-upload", APP_JS)
        self.assertIn("15000", APP_JS)
        self.assertIn("content.length > 19500", APP_JS)

    def test_plus_menu_is_styled_as_a_floating_accessible_panel(self):
        self.assertIn(".tools-menu", STYLE_CSS)
        self.assertIn(".tools-menu[hidden]", STYLE_CSS)
        self.assertIn(".plus-trigger", STYLE_CSS)

    def test_direct_mode_buttons_are_visible_in_the_composer(self):
        self.assertIn('class="quick-modebar"', APP_JS)
        self.assertIn('data-quick-task-mode="${item.id}"', APP_JS)
        self.assertIn("$$('[data-quick-task-mode]')", APP_JS)

    def test_direct_mode_buttons_share_active_mode_state_with_plus_menu(self):
        self.assertIn("$$('[data-quick-task-mode]')", APP_JS)
        self.assertIn("button.dataset.quickTaskMode === state.taskMode", APP_JS)
        self.assertIn("setTaskMode(button.dataset.quickTaskMode)", APP_JS)

    def test_small_hud_thinking_indicator_is_started_and_stopped_with_request(self):
        self.assertIn('id="spacelineThinkingCanvas"', APP_JS)
        self.assertIn('id="spacelineThinkingStatus"', APP_JS)
        self.assertIn('function startThinkingHUD()', APP_JS)
        self.assertIn('function stopThinkingHUD()', APP_JS)
        self.assertIn('startThinkingHUD();', APP_JS)
        self.assertGreaterEqual(APP_JS.count('stopThinkingHUD();'), 2)

    def test_hud_indicator_respects_reduced_motion_and_uses_compact_canvas(self):
        self.assertIn("matchMedia?.('(prefers-reduced-motion: reduce)')", APP_JS)
        self.assertIn('canvas.width = 36 * dpr', APP_JS)
        self.assertIn('.spaceline-thinking-hud', STYLE_CSS)
        self.assertIn('.quick-modebar', STYLE_CSS)


if __name__ == "__main__":
    unittest.main()
