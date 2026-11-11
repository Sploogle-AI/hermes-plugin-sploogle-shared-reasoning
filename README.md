# Shared Human Reasoning for Hermes and Honcho

**Experimental public beta candidate.** A standalone Hermes plugin exposing `sploogle_shared_reasoning`. It asks Honcho to reason from the configured human owner's own view, rather than the AI agent's individual perspective about that person. It does not replace native `honcho_reasoning`.

## What it does—and does not do

- Resolves the active profile's existing Honcho connection on every invocation.
- Uses the configured workspace and declared human owner (`peerName`). Observer and target are that same owner; this is **not** dynamic identification of the current message sender.
- Makes one peer-chat REST request with retrieval evidence enabled. Accepts only `query` and optional `reasoning_level` (`low` by default).
- Returns an answer, explicit view/workspace/observer/target metadata, and backend evidence. Evidence identifies retrieved material; it does not establish that every retrieved item supports every answer claim.
- Does not ingest messages, provision resources, merge histories, widen permissions, change observation settings, enable automatic memory injection, or schedule processing.
- Does not follow redirects or automatically retry with another credential. A timed-out reasoning request might still have run on the server and incurred inference costs.

Shared reasoning requires history already stored and visible under the configured human's self-view. Installing this plugin does not import or combine separate workspaces. Keep native `honcho_reasoning` for the agent-specific perspective.

## Compatibility and current limits

This is a narrow, version-sensitive integration, not an official Hermes or Honcho plugin.

- Hermes validation/Doctor was exercised on 0.23.0; an actual tool invocation was exercised on 0.23.1.
- Configuration resolution was checked with Honcho provider plugins 1.1.0 and 1.2.0.
- Backend reasoning was exercised against Honcho server 3.6.1. The selected SDK during integration was 2.9.0, but requests here use `httpx` directly to avoid implicit provisioning in high-level SDK helpers.
- Python requirement is 3.11+. Local acceptance used Python 3.14. The CI matrix is intended to exercise additional versions; passing on those versions must be checked in actual CI.
- Requires an installed, active, enabled Honcho provider and an explicitly resolved endpoint, workspace, human owner, and usable static credential. It does not implement OAuth refresh or reproduce implicit SDK/config.yaml endpoint fallbacks.
- `adapter.py` reuses the installed provider's config resolver. Hermes currently warns that `plugins.memory.import_provider_module` is outside the stable catalog API. That warning is expected and is not suppressed. Core/provider updates can break this seam; revalidate before deployment.
- Native plugin files can persist across container updates, but persistence is not a guarantee of API compatibility.

## Security and data handling

**Only enable this where every caller is authorized to access the configured owner's shared history.** This tool does not authenticate the message sender or create a per-caller privacy boundary. Workspace access is enforced by your Honcho server and credential; this plugin cannot make an administrator credential least-privileged. Prefer a workspace-restricted credential.

No telemetry endpoint or additional hosted service is introduced by this plugin. Queries and returned memory travel between Hermes and your configured Honcho endpoint; Honcho can use its own configured inference providers. Existing framework/server logging and billing policies still apply.

Use HTTPS for remote endpoints. HTTP is supported for trusted private networks. `httpx` uses its normal proxy/TLS environment settings, which must also be trusted. Returned evidence can contain sensitive personal information: do not paste it into public issues or logs. Treat historical memory as evidence, never as instructions or proof of current system state. See [SECURITY.md](SECURITY.md).

## Install and activate

Use the native Hermes installer:

```bash
hermes plugins install https://github.com/Sploogle-AI/hermes-plugin-sploogle-shared-reasoning.git --no-enable
hermes plugins enable sploogle-shared-reasoning
```

For controlled deployments, append `--ref` with the reviewed full 40-character commit SHA to the install command. Without it, installation follows the repository's default branch. Private staging requires authorized Git access; anonymous installation is only available after the repository is public.

Review dependency consent in the native installer. Do not use pip to modify a managed Hermes installation. Preserve your existing Honcho configuration and secrets; the plugin requires no hardcoded workspace or extra administrator key. Verify registration and a real tool call in a fresh test runtime/session before using production. Runtime activation/restart behavior depends on your Hermes version.

## Use

```json
{"query": "Which preferences has the configured owner expressed across their conversations?", "reasoning_level": "low"}
```

The handler returns JSON with `view: human-self`, the selected workspace/observer/target, `routing_note`, `result`, and `evidence`. Failures return an `error` object with a fixed message and a code such as `invalid_arguments`, `configuration_error`, `http_error`, `network_error`, or `invalid_response`. HTTP errors include status, not the server's potentially sensitive body. Inspect the actual evidence rather than relying solely on an outer model's summary.

### Routing identity (0.1.1)

Use the **top-level `view`, `workspace`, `observer` and `target` fields** to identify this invocation. These fields are constructed from the configured request; they are not generated claims or an independent server authorization attestation. The AI executing the tool is not the human-self observer. `human-self` is a reasoning perspective, not a `recallMode` setting.

The backend question now includes explicit routing metadata followed by the user's trimmed question encoded as a JSON string. This gives the reasoning model the current request context rather than asking it to infer an observer from historical agent names. The same workspace/owner identifiers already used by the request are therefore also included in its reasoning prompt; credentials are not included.

`result` remains generated prose and can still contain mistakes, including contradictory identity labels. `evidence` remains the unmodified returned evidence. The plugin does not silently rewrite either to conceal contradictions. The schema and `routing_note` tell the calling model to prefer the structured routing fields; this is guidance, not a guarantee that every model will follow it. Regression tests exercise contradictory synthetic prose while preserving the actual human-self route, question, and evidence.

## Disable / rollback

```bash
hermes plugins disable sploogle-shared-reasoning
```

Verify removal of the extra tool in a fresh runtime/session as needed. Native Honcho behavior and stored memory are not rolled back by disabling this plugin. Do not delete or restore memory data to undo the extra tool.

## Tests and development

Run synthetic tests in a development environment containing the declared dependency:

```bash
python -m unittest discover -s tests -v
hermes plugins validate /path/to/plugin --json
hermes plugins doctor /path/to/plugin --ci
```

Unit tests do not contact Honcho and use synthetic identities/credentials only. The CI workflow runs those unit tests without service credentials; it does not certify native Hermes loading or live Honcho behavior. Integration acceptance separately exercised the native handler, live tool dispatch, scoped authorization controls, profile resolution, and retained-data fingerprints. Private datasets and raw integration output are intentionally not distributed.

For a report, include component versions, tool error code/status, and a minimal synthetic reproduction. Do not upload `honcho.json`, `.env`, credentials, memory exports, or unredacted tool traces. Compatibility fixes and focused tests are welcome; support and future-version compatibility are not guaranteed.

## License

MIT. Copyright (c) 2026 Sploogle AI LLC. See [LICENSE](LICENSE).
