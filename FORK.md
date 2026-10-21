# Controlled Reason Network

Repository: https://github.com/StarRayOne/reason-network, branch `hardened`.
Baseline: upstream `c86f55d667c7a7327d14ddc7c17ca81b6d26532e` (0.12.3).
Fork version: `0.12.3-controlled.1`. Rust: `1.99.1`. Dependencies: committed `Cargo.lock`.

## Changes

- Binary self-update code is removed, including explicit `upgrade`. The legacy download installers refuse to run.
- Remote incoming messages default to `hold`. Invalid daemon configuration fails startup rather than silently accepting default settings.
- Setup requires explicit agents in noninteractive use; interactive onboarding asks which agents to connect. Existing approval settings are preserved; no new MCP blanket permission grants are added.
- Relay endpoints come from the reviewed compiled list. Dynamic vendor relay-list downloads and cached list overrides are disabled. A team's explicit custom relay is still supported.
- Incoming messages enforce the same 64 KiB text limit as outgoing messages; held message bodies are not displayed in desktop notifications.
- Membership is rechecked after connection establishment; removed or unknown peers cannot retrieve the queued outbox.
- The lockfile updates `rustls` to 0.23.46, `rustls-webpki` to 0.103.16 and `webpki-roots`/`webpki-root-certs` to 1.0.10 for RUSTSEC-2026-0346–0349 and RUSTSEC-2026-0381–0383. These are targeted patches, not a general dependency refresh.

These are focused source-review fixes, not a certification or a complete dependency audit. Normal agent permissions remain essential: the local Unix socket trusts all programs under the same operating-system user, which can approve held messages themselves. Team membership assumes trusted members; removal has the limitations described in upstream DESIGN.md. Aggregate message storage is not quota-limited.

The lockfile was checked against the OSV advisory service on 2026-10-21. `paste` 1.0.15 has the informational unmaintained advisory RUSTSEC-2024-0436, with no patched release; it remains a tracked transitive-dependency maintenance issue. Advisory matching does not prove that dependencies are free of vulnerabilities or malicious code.

## Build

Review the exact source revision before building. Do not use upstream release binaries or pipe upstream installers into a shell.

```sh
cargo fetch --locked
cargo fmt --check
cargo clippy --all-targets --frozen -- -D warnings
cargo test --frozen
cargo build --release --frozen
shasum -a 256 target/release/reason-network
```

The manually dispatched `controlled-build` GitHub workflow builds in a clean hosted runner, has read-only repository permissions and no repository credentials persisted in its checkout. Its artifact includes the source commit, Rust version, lockfile hash and binary SHA-256. Verify its successful run and exact commit before installing its artifact. This provides a controlled build record, not reproducible-build attestation.

## Install and connect selected agents

For the prepared first installation on an Apple Silicon Mac, run `sh install-controlled-macos.sh` from an ordinary Terminal. The script requires the artifact from [successful controlled build 39577655309](https://github.com/StarRayOne/reason-network/actions/runs/39577655309) in `.build/artifact`; its exact source revision is `7a7d2f0efc1b146e76e8f464f219b2f53ba13ca9`. It verifies the commit and checksum, performs a local message/MCP smoke test in isolated temporary state, records configuration fingerprints, installs, and verifies preserved settings and the login service. It refuses an existing Reason Network binary or state instead of overwriting them. This binary passed Clippy and all 136 Rust tests; its local daemon smoke test and final installation require a normal Terminal because the Codex environment denied Unix socket creation and escalation.

For a fresh checkout, obtain that artifact first:

```sh
gh run download 39577655309 --repo StarRayOne/reason-network \
  --name reason-network-controlled-aarch64-apple-darwin --dir .build/artifact
sh install-controlled-macos.sh
```

Install the verified binary as `~/.local/bin/reason-network`, outside the vendor-managed `~/.reason/bin` folder. Keep the previous binary for rollback when upgrading. Keep the state directory `~/.reason/network` owned by your user with mode 0700; its keys and invite links are private.

Before starting, write `~/.reason/network/config.toml`:

```toml
person = "dima"
share_paths = false
share_unmanaged = false
lan = false
tray = false
reason = false
auto_update = false

[inbound]
default = "hold"
```

Start a private team and explicitly select installed agents:

```sh
reason-network init dima-private --as dima --no-setup
reason-network setup --agent claude --agent codex --agent grok --dry-run
reason-network setup --agent claude --agent codex --agent grok
reason-network doctor
```

Setup backs up changed files as `.bak-reason`, adds MCP/hooks and a user login service. It preserves agent approval policies. Restart agent sessions to load MCP. Existing broad permissions, if any, remain broad; setup does not harden the agent harness itself.

Review remote messages using `reason-network held`; release selected IDs with `reason-network approve <id>` or drop them with `reason-network reject <id>`. Same-machine messages and presence metadata are not governed by remote `hold`.

Default connectivity still uses encrypted transport through Reason relay endpoints and n0 discovery. No Reason account is required. This fork does not self-host a relay or install the vendor's hosted Grok Bot MCP. Keep team links private; possession allows joining.

## Reviewed updates

1. Fetch `upstream`; review the full diff from this recorded baseline, including dependencies, build scripts, workflows, installers, relay endpoints and changes to our controls.
2. Merge only reviewed changes into a working branch. Keep the locked dependency versions unless their changes have been reviewed, and prioritize security patches.
3. Run the controlled build workflow on the exact committed revision and verify tests and artifact hashes.
4. Back up the current binary and state. Stop the daemon, atomically replace the binary, and restart the login service. Verify `--version`, `doctor`, the configuration, and MCP startup.

There is no scheduled update job and no automatic upstream merge.

## Disconnect

```sh
reason-network setup --remove --agent claude --agent codex --agent grok
reason-network stop
```

State is retained. Delete it only deliberately: it contains your identity and message history. Existing backups are retained too.
