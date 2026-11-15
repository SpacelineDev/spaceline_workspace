import { initializeApp } from 'https://www.gstatic.com/firebasejs/13.2.0/firebase-app.js';
import {
  initializeAuth, browserLocalPersistence, browserSessionPersistence, browserPopupRedirectResolver,
  onAuthStateChanged, GoogleAuthProvider, signInWithPopup, signInWithRedirect, getRedirectResult,
  signInWithEmailAndPassword, createUserWithEmailAndPassword, sendPasswordResetEmail, GithubAuthProvider,
  setPersistence, signOut,
} from 'https://www.gstatic.com/firebasejs/13.2.0/firebase-auth.js';

const $ = (selector) => document.querySelector(selector);
const gate = $('#authGate');
const shell = $('#app');
const googleButton = $('#googleSignIn');
const githubButton = $('#githubSignIn');
const config = window.SPACELINE_FIREBASE_CONFIG || {};
const message = $('#authMessage');
const signInForm = $('#signInForm');
const createAccountForm = $('#createAccountForm');
let auth = null;
let inFlight = false;
let workspaceStarted = false;
let authMode = 'sign-in';

function showMessage(text, isError = false) {
  message.textContent = text;
  message.classList.toggle('error', isError);
}

function setBusy(control, busy, label) {
  inFlight = busy;
  document.querySelectorAll('#card button, #card input').forEach((element) => {
    if (element.classList.contains('password-toggle') || element.id === 'rememberMe') return;
    element.disabled = busy;
  });
  if (control) {
    control.setAttribute('aria-busy', String(busy));
    const labelTarget = control.querySelector('.lab');
    if (labelTarget && label) labelTarget.textContent = busy ? label : control.dataset.label;
  }
}

function readableAuthError(error) {
  const code = String(error?.code || '');
  if (code.includes('popup-closed-by-user') || code.includes('cancelled-popup-request')) return 'Sign-in was cancelled. You can try again when ready.';
  if (code.includes('unauthorized-domain')) return 'This address is not authorized in Firebase. Add localhost under Authentication → Settings → Authorized domains.';
  if (code.includes('popup-blocked')) return 'Your browser blocked the sign-in window. Continuing with a secure redirect…';
  if (code.includes('network-request-failed')) return 'Could not reach Firebase. Check your connection and try again.';
  if (code.includes('operation-not-allowed')) return 'This sign-in method is not enabled for this Firebase project yet.';
  if (code.includes('invalid-credential') || code.includes('wrong-password') || code.includes('user-not-found')) return 'The email or password is incorrect.';
  if (code.includes('email-already-in-use')) return 'An account already exists for this email. Sign in instead.';
  if (code.includes('weak-password')) return 'Choose a password with at least six characters.';
  if (code.includes('account-exists-with-different-credential')) return 'An account already uses this email with another sign-in method. Sign in with that method; account linking is not available yet.';
  if (code.includes('credential-already-in-use')) return 'This GitHub account is already linked to another Spaceline account.';
  if (code.includes('user-disabled')) return 'This account has been disabled. Contact the Spaceline administrator.';
  if (code.includes('auth-domain-config-required')) return 'Firebase authDomain is missing. Check your Firebase web configuration.';
  if (code.includes('invalid-email')) return 'Enter a valid email address.';
  if (code.includes('too-many-requests')) return 'Too many attempts. Wait a moment, then try again.';
  return 'Spaceline could not complete authentication. Please try again.';
}

function setAuthMode(nextMode) {
  authMode = nextMode;
  const creating = authMode === 'create';
  signInForm.classList.toggle('hidden', creating);
  createAccountForm.classList.toggle('hidden', !creating);
  $('#authTitle').textContent = creating ? 'Create your account' : 'Welcome back';
  $('#authDescription').textContent = creating ? 'Create a secure Spaceline account to get started.' : 'Sign in to continue to your private developer workspace.';
  $('#switchPrompt').textContent = creating ? 'Already have an account?' : 'New to Spaceline?';
  $('#switchAuthMode').textContent = creating ? 'Sign in' : 'Create account';
  showMessage('Secure sign-in powered by Firebase Authentication.');
  (creating ? $('#createEmail') : $('#signInEmail')).focus();
}

async function useRequestedPersistence() {
  await setPersistence(auth, $('#rememberMe').checked ? browserLocalPersistence : browserSessionPersistence);
}

function renderAccount(user) {
  const name = user.displayName || user.email || 'Spaceline account';
  $('#accountName').textContent = name;
  $('#accountMenuName').textContent = name;
  $('#accountEmail').textContent = user.email || '';
  const avatar = $('#accountAvatar');
  avatar.replaceChildren();
  if (user.photoURL) {
    const image = document.createElement('img');
    image.src = user.photoURL;
    image.alt = '';
    image.referrerPolicy = 'no-referrer';
    image.onerror = () => { avatar.textContent = (name[0] || 'S').toUpperCase(); };
    avatar.append(image);
  } else avatar.textContent = (name[0] || 'S').toUpperCase();
}

async function startWorkspace(user) {
  renderAccount(user);
  gate.classList.add('hidden');
  shell.hidden = false;
  if (workspaceStarted) return;
  workspaceStarted = true;
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    if (url.origin === location.origin && url.pathname.startsWith('/api/')) {
      const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
      const current = auth.currentUser;
      if (current) {
        try { headers.set('Authorization', `Bearer ${await current.getIdToken()}`); }
        catch (error) { void signOut(auth); throw error; }
      }
      const response = await nativeFetch(input, {...init, headers});
      if (response.status === 401 && auth.currentUser) void signOut(auth);
      return response;
    }
    return nativeFetch(input, init);
  };
  const script = document.createElement('script');
  script.src = '/assets/app.js?v=0.9.6';
  script.onerror = () => showMessage('Spaceline could not load the workspace. Refresh this page to try again.', true);
  document.body.append(script);
}

async function signInWithProvider(button, provider, label) {
  if (inFlight || !auth) return;
  button.dataset.label = label;
  setBusy(button, true, 'Connecting securely…');
  try {
    await useRequestedPersistence();
    await signInWithPopup(auth, provider);
  } catch (error) {
    const code = String(error?.code || '');
    if (code.includes('popup-blocked') || code.includes('operation-not-supported-in-this-environment')) {
      showMessage('Your browser cannot open the sign-in popup. Continuing with a secure redirect…');
      try { await signInWithRedirect(auth, provider); }
      catch (redirectError) { showMessage(readableAuthError(redirectError), true); }
    } else showMessage(readableAuthError(error), true);
  } finally {
    setBusy(button, false);
  }
}

async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({prompt: 'select_account'});
  await signInWithProvider(googleButton, provider, 'Continue with Google');
}

async function signInWithGithub() {
  const provider = new GithubAuthProvider();
  provider.addScope('read:user');
  provider.addScope('user:email');
  await signInWithProvider(githubButton, provider, 'Continue with GitHub');
}

async function submitEmailForm(event) {
  event.preventDefault();
  if (inFlight || !auth) return;
  const isCreate = authMode === 'create';
  const form = isCreate ? createAccountForm : signInForm;
  if (!form.reportValidity()) return;
  const email = $('#'+(isCreate ? 'createEmail' : 'signInEmail')).value.trim();
  const password = $('#'+(isCreate ? 'createPassword' : 'signInPassword')).value;
  const button = isCreate ? $('#createAccount') : $('#go');
  button.dataset.label = isCreate ? 'Create account' : 'Sign in';
  setBusy(button, true, isCreate ? 'Creating account…' : 'Signing in…');
  try {
    await useRequestedPersistence();
    if (isCreate) await createUserWithEmailAndPassword(auth, email, password);
    else await signInWithEmailAndPassword(auth, email, password);
  } catch (error) {
    showMessage(readableAuthError(error), true);
  } finally {
    setBusy(button, false);
  }
}

async function resetPassword() {
  if (!auth || inFlight) return;
  const email = $('#signInEmail').value.trim();
  if (!email) {
    $('#signInEmail').focus();
    showMessage('Enter your email address first, then choose Forgot password.', true);
    return;
  }
  try {
    await sendPasswordResetEmail(auth, email);
    showMessage('If this address has an account, Firebase will send a password-reset email.');
  } catch (error) {
    showMessage(readableAuthError(error), true);
  }
}

googleButton.addEventListener('click', signInWithGoogle);
githubButton.addEventListener('click', signInWithGithub);
signInForm.addEventListener('submit', submitEmailForm);
createAccountForm.addEventListener('submit', submitEmailForm);
$('#switchAuthMode').addEventListener('click', () => setAuthMode(authMode === 'create' ? 'sign-in' : 'create'));
$('#forgotPassword').addEventListener('click', resetPassword);
document.querySelectorAll('[data-password-toggle]').forEach((button) => button.addEventListener('click', () => {
  const input = document.getElementById(button.dataset.passwordToggle);
  const reveal = input.type === 'password';
  input.type = reveal ? 'text' : 'password';
  button.textContent = reveal ? 'Hide' : 'Show';
  button.setAttribute('aria-label', `${reveal ? 'Hide' : 'Show'} password`);
}));

function disableAuthentication(messageText) {
  document.querySelectorAll('#card button, #card input').forEach((element) => { element.disabled = true; });
  showMessage(messageText, true);
}

if (!window.SPACELINE_FIREBASE_CONFIGURED || !config.apiKey) {
  const missing = Array.isArray(window.SPACELINE_FIREBASE_MISSING) ? window.SPACELINE_FIREBASE_MISSING.join(', ') : 'Firebase web variables';
  disableAuthentication(`Firebase is not configured. Add ${missing} to .env, then restart Spaceline.`);
} else if (!window.SPACELINE_FIREBASE_BACKEND_READY) {
  disableAuthentication('Firebase server-side token verification is unavailable. Check your Firebase web configuration and internet connection, then restart Spaceline.');
} else {
  try {
    const firebaseApp = initializeApp(config);
    auth = initializeAuth(firebaseApp, { persistence: browserLocalPersistence, popupRedirectResolver: browserPopupRedirectResolver });
    getRedirectResult(auth).catch((error) => showMessage(readableAuthError(error), true));
    onAuthStateChanged(auth, (user) => {
      if (user) void startWorkspace(user);
      else { shell.hidden = true; gate.classList.remove('hidden'); }
    }, () => showMessage('Could not restore your sign-in session. Sign in again to continue.', true));
  } catch (_) {
    disableAuthentication('Firebase could not initialize. Check the Firebase web configuration and restart Spaceline.');
  }
}

$('#accountMenuButton').addEventListener('click', () => {
  const menu = $('#accountMenu');
  const open = menu.classList.toggle('hidden') === false;
  $('#accountMenuButton').setAttribute('aria-expanded', String(open));
});
async function leaveAccount() {
  $('#accountMenu').classList.add('hidden');
  $('#accountMenuButton').setAttribute('aria-expanded', 'false');
  try { await signOut(auth); }
  catch (_) { showMessage('Could not sign out. Check your connection and try again.', true); }
}
$('#signOut').addEventListener('click', leaveAccount);
$('#switchAccount').addEventListener('click', leaveAccount);
document.addEventListener('click', (event) => {
  if (!event.target.closest('.sidebar-footer')) {
    $('#accountMenu')?.classList.add('hidden');
    $('#accountMenuButton')?.setAttribute('aria-expanded', 'false');
  }
});
