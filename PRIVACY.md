# Spaceline Privacy Policy

**Effective date: November 17, 2026**

Spaceline is a local-first AI and coding workspace for Windows. This policy explains what information Spaceline processes, where it is stored, and when it is sent to other services.

## 1. Who operates Spaceline

Spaceline is maintained as an independent software project by the SpacelineDev project account.

For privacy questions or requests, use the contact options on the [SpacelineDev GitHub profile](https://github.com/SpacelineDev). Please do not post passwords, API keys, identity documents, or other sensitive personal information in public issues.

## 2. Information Spaceline processes

Depending on the features you use, Spaceline may process:

- **Account and sign-in information:** Firebase Authentication user identifier and authentication tokens, plus the information handled by the sign-in provider you choose (Google, GitHub, or email/password).
- **Workspace information:** chats, project files, notes, settings, provider/connection metadata, and other workspace content you create or import.
- **Credentials:** AI-provider API keys that you choose to save. Spaceline stores key secrets in the current Windows account's Credential Manager; key labels and related metadata may be stored in the local workspace database.
- **AI requests and attachments:** prompts, selected conversation context, and files or text you explicitly submit to an AI provider through Spaceline.
- **Browser activity:** URLs and page content that you choose to open or inspect using Spaceline's embedded browser.
- **Generated content:** images and related prompt/non-secret generation metadata created through Image Studio.

Spaceline does not need access to your everyday browser's cookies or profile. Its embedded Chromium browser uses a separate Spaceline-managed profile.

## 3. Where information is stored

Spaceline is designed to run on your Windows computer. By default, workspace files and the SQLite workspace database are stored locally in your Windows user profile, under Documents/Spaceline (or in the workspace directory you configure).

API-key secrets are stored in Windows Credential Manager. Generated images are stored locally in the Spaceline workspace's Generated Images folder.

Spaceline is not a hosted multi-user chat service. Your local workspace content is not automatically uploaded to a Spaceline-operated cloud storage account. Firebase Authentication is used for sign-in and identity verification; it does not mean that your local chats and project files are automatically synchronized to the cloud.

Anyone who can access your Windows account or local files may be able to access locally stored workspace information. Use a protected Windows account and keep your device secure.

## 4. Services you choose to use

Spaceline connects to third-party services to provide features you request:

- **Firebase Authentication:** verifies sign-in and account identity. Google, GitHub, and email/password sign-in are supported when configured.
- **AI and image providers:** when you send a prompt, attach content, or request an image, the relevant request is sent to the provider selected by you. Depending on your configuration, this may include OpenAI-compatible services, Anthropic, Google Gemini, Ollama, AI Horde, Eden AI, or another custom provider.
- **Websites you visit:** when you use the embedded browser, the websites you choose to visit receive the normal connection information and requests needed to serve their pages.

These providers and websites operate under their own privacy policies and terms. They may process, retain, or use information according to their own settings and policies. Review those terms before sending sensitive information. Spaceline does not control third-party data practices, model training policies, service availability, or retention periods.

Your prompts and attachments are sent only as part of the provider/model or browser action you select. Do not submit information to an AI provider unless you are comfortable with that provider receiving it.

## 5. Sharing and disclosure

The project does not sell your personal information. Spaceline does not operate an advertising profile or sell workspace content.

Information may be transmitted to the third-party services described above when you actively use their features. You are responsible for choosing the provider, account, model, and content you submit.

## 6. Data retention and deletion

Local chats, projects, settings, and generated files remain on your device until you delete them or remove the workspace. Backups may retain copies until you remove those backups.

Saved API keys remain in Windows Credential Manager until you remove them through the relevant Spaceline controls or Windows Credential Manager.

Firebase account information is handled by Firebase Authentication and the sign-in provider. To request help with a Spaceline-related privacy question, use the contact options on the SpacelineDev GitHub profile. Deleting local files does not necessarily delete information held by a third-party provider, and deleting a third-party account does not automatically delete local workspace files.

## 7. Security

Spaceline includes safeguards such as local-only server binding, protected local API routes, per-account workspace separation, and storage of API-key secrets in Windows Credential Manager. No software or storage method is completely secure. Keep Spaceline updated, protect your Windows account, and never share your .env file, service-account credentials, OAuth secrets, or API keys.

The local command runner executes with your Windows account permissions and is not an operating-system sandbox. Only run commands and projects you trust.

## 8. Children

Spaceline is a general-purpose developer and productivity application and is not designed specifically for children. If you believe a child has provided personal information through a service used with Spaceline, contact the relevant service and use the contact options in Section 1.

## 9. Changes to this policy

This policy may be updated when Spaceline's features, integrations, or data practices change. The latest version will be published in the Spaceline GitHub repository. The effective date at the top indicates when this version was last updated.

## 10. Contact

For privacy questions or requests, visit [SpacelineDev on GitHub](https://github.com/SpacelineDev) and use the available contact options. Do not include secrets or sensitive personal information in public posts.

---

This policy describes the documented behavior of Spaceline 0.9.6. It is general product information, not legal advice. Review it for accuracy and obtain legal advice if you need a policy tailored to specific jurisdictions or distribution requirements.
