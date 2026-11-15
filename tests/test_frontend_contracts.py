from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
STYLE_CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


def test_chat_sidebar_has_a_separate_delete_control():
    assert "data-chat-delete" in APP_JS
    assert "data-chat-open" in APP_JS


def test_current_chat_has_delete_action():
    assert 'id="deleteCurrentChat"' in APP_JS
    assert "deleteChat(state.activeChatId)" in APP_JS


def test_chat_search_results_can_be_deleted_without_opening_them():
    assert "data-chat-delete" in APP_JS
    assert "deleteChat(deleteButton.dataset.chatDelete)" in APP_JS


def test_delete_confirmation_and_state_cleanup_are_present():
    assert "Delete this conversation and all of its messages?" in APP_JS
    assert "state.chats = state.chats.filter" in APP_JS
    assert "state.activeChatId = null" in APP_JS


def test_delete_controls_have_keyboard_accessible_labels_and_styles():
    assert 'aria-label="Delete chat"' in APP_JS
    assert ".chat-delete" in STYLE_CSS


def test_model_catalog_never_calls_listed_ids_available_without_a_test():
    assert "Search ${models.length} model IDs…" in APP_JS
    assert "model IDs listed · access not yet verified" in APP_JS
    assert "verified working models" in APP_JS
    assert "available models…" not in APP_JS


def test_model_access_status_distinguishes_auth_and_provider_outage():
    assert "error.status===401?'invalid_key'" in APP_JS
    assert "error.status===503||error.status===502?'provider_down'" in APP_JS


def test_remote_http_endpoint_is_marked_blocked_not_local_http():
    assert "BLOCKED · remote HTTP; use HTTPS" in APP_JS
    assert "blocked-http" in APP_JS


def test_document_reader_ui_has_visible_metadata_warnings_and_safe_text_view():
    assert "document-analysis-preview" in APP_JS
    assert "document-warning" in APP_JS
    assert "Nothing in the file is executed" in APP_JS
    assert ".document-analysis-preview" in STYLE_CSS
    assert ".document-extracted-text" in STYLE_CSS


def test_project_file_search_ui_and_document_attachment_flow_are_wired():
    assert "/api/files/search" in APP_JS
    assert "/api/files/analyze-upload" in APP_JS
    assert "askAboutActiveDocument" in APP_JS
    assert "state.attachments.push" in APP_JS
    assert "Search code and documents" in APP_JS


def test_document_search_and_preview_have_mobile_layout_rules():
    assert "@media(max-width:720px){.document-analysis-preview" in STYLE_CSS
    assert ".project-file-search" in STYLE_CSS
    assert ".file-search-result" in STYLE_CSS


def test_document_preview_discloses_spreadsheet_formula_limit_and_empty_search_state():
    assert "Formula expressions and cached values are shown" in APP_JS
    assert "No matching files or passages" in APP_JS


def test_browser_and_terminal_copy_does_not_overclaim_chrome_or_sandbox_access():
    assert "separate, persistent Chromium profile" in APP_JS
    assert "not your everyday Chrome window" in APP_JS
    assert "this is not an operating-system sandbox" in APP_JS
    assert "Integration status" in APP_JS
    assert "not yet integrated" in APP_JS


def test_attach_menu_advertises_supported_documents_and_real_size_limits():
    assert "Documents and source files" in APP_JS
    assert "PDF · DOCX · XLSX · PPTX · CSV/TSV" in APP_JS
    assert "20 MB each" in APP_JS
    assert "15,000 extracted characters" in APP_JS

    def test_browser_right_panel_has_command_controls_and_safe_examples(self):
        source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="browserCommandForm"', source)
        self.assertIn('id="browserCommandInput"', source)
        self.assertIn("/api/browser/command", source)
        self.assertIn("Run browser command", source)
        self.assertIn("browserCommandBusy", source)
        self.assertIn("ordinary checkboxes", source)
        self.assertNotIn("does not provide full manual browser interaction", source)

    def test_provider_cards_offer_bulk_model_verification_and_verified_only_results(self):
        source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("Test all models", source)
        self.assertIn("/models/verify-all", source)
        self.assertIn("verifiedModelsByProfile", source)

    def test_thinking_word_has_subtle_shimmer_animation(self):
        source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
        css = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn('class="thinking-word"', source)
        self.assertIn("@keyframes thinkingShine", css)


def test_frontend_templates_do_not_contain_literal_empty_buttons():
    import re
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert re.search(r"<button\b[^>]*>\s*</button>", source, re.I | re.S) is None


def test_verified_model_access_is_persisted_with_account_fingerprint_and_expiry():
    assert "spaceline.verifiedModels.v1" in APP_JS
    assert "profileVerificationFingerprint" in APP_JS
    assert "verified_at" in APP_JS
    assert "MODEL_VERIFICATION_TTL_MS" in APP_JS
    assert "persistVerifiedModelResults" in APP_JS


def test_provider_change_clears_a_model_id_from_the_previous_provider():
    assert "previousProvider" in APP_JS
    assert "name=model" in APP_JS or "[name=\\\"model\\\"]" in APP_JS
    assert "modelInput.value = ''" in APP_JS


def test_model_selection_never_silently_falls_back_from_a_disabled_saved_active_profile():
    assert "state.profiles.find(p => p.id === data.active_profile_id && p.enabled !== false)" in APP_JS
    assert "state.profiles.find(p => p.enabled !== false && p.model)" not in APP_JS
    assert "function selectedProfile() { return state.profiles.find(p => p.id === state.activeProfileId && p.enabled !== false) || null; }" in APP_JS
    load_providers = APP_JS[APP_JS.index("async function loadProviders"):APP_JS.index("async function loadKeys")]
    assert "api('/api/providers/active'" not in load_providers


def test_custom_openai_compatible_keys_are_saved_under_canonical_provider_id():
    assert "savedProvider = form.get('provider') === '__custom__' ? 'openai-compatible'" in APP_JS


def test_premium_theme_uses_forest_charcoal_and_variable_font_stack():
    assert "--bg:#151b17" in STYLE_CSS
    assert "--accent:#d8bd78" in STYLE_CSS
    assert "Segoe UI Variable" in STYLE_CSS
    assert ".brand-lockup" in STYLE_CSS


def test_model_picker_never_keeps_a_model_that_failed_the_latest_bulk_check():
    assert "verifiedIds.has(profile?.model)" in APP_JS
    assert "Choose a model that passed the latest access check" in APP_JS
    assert "id=\"testManualModel\"" in APP_JS
    assert "modelChecks.get(model)?.state !== 'verified'" in APP_JS
    assert "verified working models" in APP_JS


def test_model_bulk_results_surface_failure_reasons_without_exposing_provider_errors():
    assert "failure_categories" in APP_JS
    assert "provider unavailable" in APP_JS.lower()
    assert "quota/credits" in APP_JS
    assert "full-scan results not confirmed" in APP_JS
    assert "manual_models" in APP_JS


def test_premium_modal_theme_targets_the_actual_modal_element():
    assert ".modal{width:min(620px,100%);padding:24px;background:linear-gradient" in STYLE_CSS
    assert ".modal-card input" not in STYLE_CSS


def test_model_picker_allows_manual_model_verification_even_after_bulk_scan():
    assert "Or test an exact model ID manually" in APP_JS
    assert "manual.disabled=true" not in APP_JS
    assert "if(verifiedIds && models.length)" not in APP_JS
    assert "bulkResult?.status==='complete' && models.length ? 'disabled'" not in APP_JS


def test_model_warning_distinguishes_inconclusive_provider_failures_from_model_rejection():
    assert "hasInconclusiveFailures" in APP_JS
    assert "quota or availability errors do not prove the model is unsupported" in APP_JS


def test_missing_provider_key_is_not_mislabeled_as_a_network_error():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "No usable API key is saved for this connection." in source
    assert 'if "no usable api key" in str(error).lower():' in source
    assert 'return "missing_key"' in source


def test_manual_model_probe_is_persisted_even_without_a_prior_bulk_scan():
    assert "manual_only:true" in APP_JS
    assert "manual_only:Boolean(record.manual_only)" in APP_JS
    assert "state.verifiedModelsByProfile[profile.id] = working" in APP_JS
    assert "state.modelsByProfile[profile.id] = working.map(item=>item.id)" in APP_JS
    assert "state.verifiedModelsByProfile[profile.id]=saved.working_models" in APP_JS
    assert "models = models.filter(id=>verifiedIds.has(id))" in APP_JS


def test_classic_workspace_has_a_searchable_keyboard_command_palette():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    css = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8")
    assert "function openCommandPalette()" in source
    assert 'id="commandPaletteInput"' in source
    assert "data-command-id" in source
    assert "Ctrl+K" in source
    assert ".command-palette" in css


def test_workspace_preferences_persist_between_restarts():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "spaceline.workspacePreferences.v1" in source
    assert "loadWorkspacePreferences" in source
    assert "saveWorkspacePreferences" in source
    assert "workbenchCollapsed" in source


def test_classic_premium_theme_uses_restrained_graphite_green_surface_system():
    css = (Path(__file__).resolve().parents[1] / "static" / "style.css").read_text(encoding="utf-8").lower()
    assert "--bg:#121614" in css
    assert "--panel:#181c1a" in css
    assert "rgba(255,255,255,.08)" in css
    assert "--accent:#cdb77e" in css
    assert ".command-palette" in css
    assert "prefers-reduced-motion:reduce" in css


def test_command_palette_supports_keyboard_navigation_and_closes_cleanly():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "commandPaletteActiveIndex" in source
    assert "ArrowDown" in source and "ArrowUp" in source
    assert "data-command-close" in source



def test_composer_drafts_are_saved_per_profile_and_chat_with_a_bounded_store():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    assert "function currentDraftKey()" in source
    assert "function loadComposerDraft()" in source
    assert "function persistComposerDraft(value)" in source
    assert "slice(0, 16)" in source
    assert "persistComposerDraft(input.value)" in source
    assert "${escapeHTML(loadComposerDraft())}" in source


def test_command_palette_exposes_core_workspace_destinations():
    source = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    for command in ("new-chat", "search", "projects", "artifacts", "browser", "code", "providers", "skills", "new-project", "new-artifact"):
        assert f"id:'{command}'" in source


def test_image_studio_has_its_own_navigation_and_topbar_entrypoint():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert 'data-view="images"' in html
    assert 'id="openImageStudio"' in html
    assert "state.view === 'images'" in APP_JS
    assert "function renderImageStudioPage" in APP_JS
    assert "function bindImageStudioPage" in APP_JS


def test_image_studio_is_a_standalone_polished_creation_workspace():
    assert 'class="image-studio-page"' in APP_JS
    assert 'class="image-studio-hero"' in APP_JS
    assert 'id="imageGenerateForm"' in APP_JS
    assert 'id="imageGallery"' in APP_JS
    assert ".image-studio-page" in STYLE_CSS
    assert ".image-studio-hero" in STYLE_CSS


def test_all_saved_api_keys_can_be_tested_without_exposing_secrets():
    assert 'id="testAllSavedKeys"' in APP_JS
    assert "async function testAllSavedKeys" in APP_JS
    assert "data-key-test" in APP_JS
    assert "/api/keys/${encodeURIComponent(key.id)}/test" in APP_JS
    assert "API key test complete" in APP_JS
    assert "secret" not in APP_JS[APP_JS.index("async function testAllSavedKeys"):APP_JS.index("async function testAllSavedKeys") + 1800].lower()


def test_bulk_saved_key_test_is_sequential_and_preserves_per_key_results():
    start = APP_JS.index("async function testAllSavedKeys")
    end = APP_JS.find("\n  function ", start + 10)
    segment = APP_JS[start:end if end > -1 else None]
    assert "for (const key of keys)" in segment
    assert "await api(`/api/keys/${encodeURIComponent(key.id)}/test`" in segment
    assert "state.keyTestResults[key.id]" in segment
    assert "setTimeout" not in segment


def test_image_generation_handles_stale_local_session_without_retrying_upstream():
    assert "error.sessionExpired" in APP_JS
    assert "spaceline.imageSessionRecovery.v1" in APP_JS
    assert "window.location.reload()" in APP_JS
    assert "never retry the image request automatically" in APP_JS


def test_image_session_recovery_restores_prompt_after_server_restart():
    assert "Date.now() - Number(recovery.saved_at || 0) < 10 * 60 * 1000" in APP_JS
    assert "localStorage.removeItem('spaceline.imageSessionRecovery.v1')" in APP_JS
    assert "state.imagePrompt = String(recovery.prompt).slice(0, 4000)" in APP_JS


def test_personalization_and_live_code_preview_are_real_ui_features():
    assert "Personalization" in APP_JS
    assert "personalizationForm" in APP_JS
    assert "/api/personalization" in APP_JS
    assert "code-preview-split" in APP_JS
    assert "saveWorkbenchCode" in APP_JS
    assert "previewVersion" in APP_JS
    assert "thinking_style" in APP_JS
    assert "scheduleWorkbenchSave" in APP_JS
    assert "refreshWorkbenchPreview" in APP_JS
    assert "openLivePreview" in APP_JS
    assert "--mono-bg:#090909" in STYLE_CSS.lower() and "color:#fff" in STYLE_CSS.lower()


def test_topbar_preview_saves_unsaved_edits_from_either_editor_before_switching():
    handler_start = APP_JS.index("$('#openLivePreview')?.addEventListener('click'")
    handler_end = APP_JS.index("$('#footerSettings')", handler_start)
    handler = APP_JS[handler_start:handler_end]
    assert "if (state.editorDirty)" in handler
    assert "state.view === 'projects' ? await saveProjectFile() : await saveWorkbenchEditor(false)" in handler
    assert "if (!saved) { toast('Save failed. Preview was not opened.'); return; }" in handler


def test_deep_think_does_not_force_browser_panel_or_browser_refresh():
    set_mode_start = APP_JS.index("function setTaskMode(mode)")
    set_mode_end = APP_JS.index("async function loadBrowserScreenshot", set_mode_start)
    set_mode = APP_JS[set_mode_start:set_mode_end]
    assert "if (['web_search','deep_research'].includes(mode))" in set_mode
    assert "['deep_think','architect','build','debug'" in set_mode

    workbench_start = APP_JS.index("function openWorkbenchForTask(prompt)")
    workbench_end = APP_JS.index("async function generateImage", workbench_start)
    workbench = APP_JS[workbench_start:workbench_end]
    assert "['web_search','deep_research'].includes(state.taskMode)" in workbench

    completion_start = APP_JS.index("pushActivity('Response complete'")
    completion_end = APP_JS.index("const data = await api(`/api/chats/", completion_start)
    completion = APP_JS[completion_start:completion_end]
    assert "state.researchTaskActive" not in completion
    assert "refreshBrowserPage" not in completion


def test_codex_style_git_review_panel_is_visible_and_read_only():
    assert "['review','Review']" in APP_JS
    assert "function renderGitReview()" in APP_JS
    assert "/api/projects/${encodeURIComponent(state.selectedProject)}/git-review" in APP_JS
    assert "id=\"refreshGitReview\"" in APP_JS
    assert "project_git_diff" not in APP_JS  # Git operations stay behind the read-only server endpoint.
    assert ".git-review-diff" in STYLE_CSS
