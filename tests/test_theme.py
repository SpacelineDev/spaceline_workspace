from pathlib import Path


def test_workspace_uses_a_monochrome_black_white_palette():
    css = (Path(__file__).parents[1] / "static" / "style.css").read_text(encoding="utf-8").lower()
    assert "--mono-bg:#090909" in css
    assert "--mono-panel:#171717" in css
    assert "--mono-text:#f5f5f5" in css
    assert "--mono-muted:#b8b8b8" in css
    assert "monochrome workspace theme" in css
    assert "prefers-reduced-motion" in css


def test_chat_workspace_has_mode_selector_and_adaptive_workbench():
    root = Path(__file__).parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    css = (root / "static" / "style.css").read_text(encoding="utf-8")
    for mode in ("chat", "web_search", "deep_think", "deep_research"):
        assert f"id:'{mode}'" in js
    assert 'data-task-mode="${item.id}"' in js
    assert "workbench" in js
    assert ".chat-workspace" in css
    assert "workbench" in html or "workbench" in css




def test_086_floating_controls_and_cursor_are_accessible():
    root = Path(__file__).parents[1]
    css = (root / "static" / "style.css").read_text(encoding="utf-8")
    js = (root / "static" / "app.js").read_text(encoding="utf-8")
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    assert ".button.primary" in css and "--float-shadow" in css
    assert ".spaceline-cursor" in css and "prefers-reduced-motion" in css
    assert "function setupCustomCursor()" in js
    assert 'id="spacelineCursor"' in html
