# Security

This is an experimental integration, not an authorization service. No stable-version support window or guaranteed security response time is promised.

## Deployment boundary

The tool reads the configured human owner's self-view, regardless of the identity of the message sender. Only enable it for callers already authorized to see that owner's shared history. Do not expose it to unrelated clients or public chats. Use server-enforced workspace restrictions and a least-privileged credential; a workspace name is not an access control by itself.

The plugin resolves the existing profile configuration at invocation time. It does not distribute credentials, refresh OAuth, provision peers, change memberships or retry a denied operation with an administrator key. The operator controls the endpoint and credential. Use HTTPS outside trusted private networks and audit inherited proxy settings.

Queries and retrieved evidence can be sensitive. Existing Hermes/Honcho/model-provider processing, logging and retention still apply. Memory content is untrusted data, not executable instructions. Exact returned evidence and generated summaries must be assessed separately.

## Reporting

Do not post credentials, personal data, exported memories, connection strings or exploitable vulnerability details in a public issue. Ordinary bug reports should use synthetic examples and sanitized version/error metadata.

**Publication gate:** maintainers must configure GitHub private vulnerability reporting or publish an approved private contact before making this candidate public. No private reporting channel is claimed to exist yet.

## Release hygiene

- Publish only reviewed source, synthetic tests and generic documentation; exclude runtime configuration, private integration data and internal deployment notes.
- Review all public commits and author metadata, not just the current working tree.
- Pin a reviewed public commit for deployment and revalidate after Hermes/provider/server upgrades.
- A clean pattern scan is limited screening, not proof that no sensitive information exists.
