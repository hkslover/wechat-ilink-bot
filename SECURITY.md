# Security Policy

## Supported Versions

`wechat-ilink-bot` is currently in the `0.x` phase.

At this stage:

- only the latest minor release is considered supported for security fixes
- older `0.x` releases may not receive backported patches
- fixes may ship as part of the next public release rather than as a standalone patch release

If you are reporting a vulnerability, always include the exact package version or commit you tested.

## Reporting a Vulnerability

Please do **not** open public issues for suspected security vulnerabilities.

Use one of these private channels instead:

1. GitHub private vulnerability reporting (Security Advisory) for this repository, if enabled
2. Direct contact through maintainer contact methods listed on the repository profile

When reporting, please include as much of the following as possible:

- affected version
- reproduction steps
- configuration details relevant to the issue
- impact assessment
- whether credentials, tokens, local state, or webhook endpoints are involved
- suggested mitigation, if known

We will acknowledge reports as quickly as possible and coordinate disclosure once a fix is available.

## Coordinated Disclosure

Please allow maintainers reasonable time to investigate, reproduce, and fix the issue before public disclosure.

Our general process is:

1. acknowledge receipt
2. validate and assess impact
3. prepare a fix or mitigation
4. release the fix
5. coordinate disclosure details when appropriate

If a report is accepted, we may ask for additional reproduction details or environment information during triage.

## Security Boundaries in This Repository

This project handles local bot credentials and may expose outbound-send capability through a webhook server. The items below are especially security-sensitive:

- bot tokens stored in local account credentials
- `current_user.json` account metadata
- long-poll sync state in `sync.json`
- conversation `context_token` data in `context_tokens.json`
- webhook access control through API keys

## Local State and Credential Storage

By default, SDK state is stored under:

```text
~/.wechat_bot/
├── current_user.json
└── {account_id}/
    ├── credentials.json
    ├── sync.json
    └── context_tokens.json
```

Important details:

- `{account_id}/credentials.json` may contain the bot token for that account
- `current_user.json` stores account metadata and does **not** store the token by default
- `sync.json` stores long-poll cursor state
- `context_tokens.json` stores conversation context tokens used by follow-up interactions

Treat the entire state directory as sensitive local application data.

## Local File Security Behavior

Where supported by the platform, the SDK attempts to harden local state storage by:

- using directory mode `700`
- using file mode `600`
- writing JSON files via atomic replacement to reduce corruption risk during interrupted writes

These protections improve the default posture, but they are not a substitute for host-level security.

## Safe Operating Recommendations

If you use this SDK locally or in automation environments:

- do not commit `~/.wechat_bot` or any copied state directory into version control
- do not share state directories between untrusted users
- avoid placing state files in broadly readable temporary directories
- rotate credentials and re-login if you suspect token exposure
- redact tokens, webhook keys, and sensitive file contents from logs, screenshots, and issue reports

## Webhook Security Notes

The webhook server can expose a `/send` endpoint for outbound text delivery.

Recommended precautions:

- prefer binding to `127.0.0.1` unless remote access is explicitly required
- always configure an API key when exposing `/send` beyond a trusted local environment
- disable GET `/send` if your deployment only needs POST
- place the service behind your own network controls, reverse proxy, or gateway when applicable

The webhook implementation intentionally returns a generic `502 Failed to send message` response for downstream send failures so that internal exception details are not exposed to external callers.

## What to Include in Security Reports

A high-quality report should include:

- exact dependency version or commit
- minimal reproduction steps
- whether the issue is local-only, network-reachable, or requires prior access
- expected impact on confidentiality, integrity, or availability
- whether the problem affects token storage, webhook auth, polling/session handling, or media handling

If you are unsure whether an issue is security-sensitive, report it privately first.
