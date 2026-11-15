from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
AUTH = (ROOT / "static" / "auth.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "style.css").read_text(encoding="utf-8")


class AuthLoginContractTests(unittest.TestCase):
    def test_login_route_has_real_firebase_auth_controls_and_logo(self):
        for fragment in ('src="/assets/spaceline-mark.svg"', 'id="googleSignIn"', 'id="githubSignIn"', 'class="auth-intro"', 'id="signInForm"', 'id="createAccountForm"', 'id="forgotPassword"', 'id="rememberMe"', 'data-password-toggle="signInPassword"', 'id="app" class="app-shell" hidden'):
            self.assertIn(fragment, INDEX)

    def test_auth_module_uses_firebase_methods_and_never_stores_passwords(self):
        for method in ("signInWithPopup", "signInWithRedirect", "getRedirectResult", "GithubAuthProvider", "signInWithEmailAndPassword", "createUserWithEmailAndPassword", "sendPasswordResetEmail", "setPersistence", "signOut"):
            self.assertIn(method, AUTH)
        self.assertNotIn("localStorage", AUTH)
        self.assertNotIn("sessionStorage", AUTH)

    def test_login_card_has_no_position_animation_or_pointer_behavior(self):
        card_rules = re.findall(r"\.auth-card\{([^}]*)\}", CSS)
        self.assertTrue(card_rules)
        self.assertTrue(all("transform:" not in rule and "animation:" not in rule for rule in card_rules))
        self.assertNotIn("mousemove", AUTH)
        self.assertNotIn("pointermove", AUTH)

    def test_code_background_and_reduced_motion_are_present(self):
        self.assertIn('class="auth-code-field"', INDEX)
        for fragment in ("const", "&lt;/&gt;", "function", "import"):
            self.assertIn(fragment, INDEX)
        self.assertIn("@media(prefers-reduced-motion:reduce)", CSS)
        self.assertIn("auth-code-drift", CSS)

    def test_firebase_config_is_declared_before_initialization(self):
        self.assertIn("const config = window.SPACELINE_FIREBASE_CONFIG || {};", AUTH)
        self.assertIn("if (!window.SPACELINE_FIREBASE_CONFIGURED || !config.apiKey)", AUTH)

    def test_github_sign_in_is_wired(self):
        self.assertIn("githubButton.addEventListener('click', signInWithGithub)", AUTH)
        self.assertIn("provider.addScope('read:user')", AUTH)

    def test_landing_page_has_intro_and_login_card(self):
        self.assertIn('class="auth-layout"', INDEX)
        self.assertIn('One space for', INDEX)
        self.assertIn('class="auth-feature-list"', INDEX)
