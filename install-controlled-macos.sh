#!/bin/sh
set -eu
umask 077

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
task_dir="$repo_dir/.build"
artifact_dir="$task_dir/artifact"
expected_commit=7a7d2f0efc1b146e76e8f464f219b2f53ba13ca9
bin_dir="$HOME/.local/bin"
state_dir="$HOME/.reason/network"
binary="$bin_dir/reason-network"

# This installation uses the default state path, including the generated hooks.
unset REASON_NETWORK_HOME TINCAN_HOME REASON_NETWORK_NO_SERVICE TINCAN_NO_SERVICE

test "$(uname -s)" = Darwin
test "$(uname -m)" = arm64
test "$(cat "$artifact_dir/SOURCE_COMMIT")" = "$expected_commit"
(cd "$artifact_dir" && shasum -a 256 -c SHA256SUMS)
if test -e "$binary" || test -L "$binary" || test -e "$state_dir" || test -L "$state_dir"; then
    printf '%s\n' 'Existing binary/state found; refusing to overwrite. Review before upgrading.' >&2
    exit 1
fi

python3 -m venv "$task_dir/venv"
"$task_dir/venv/bin/python3" "$repo_dir/tests/e2e/controlled_smoke.py"
"$task_dir/venv/bin/python3" "$repo_dir/scripts/check-controlled-install.py" before

mkdir -p "$bin_dir" "$HOME/.reason"
mkdir -m 700 "$state_dir"
cat > "$state_dir/config.toml" <<'CONFIG'
person = "dima"
share_paths = false
share_unmanaged = false
lan = false
tray = false
reason = false
auto_update = false

[inbound]
default = "hold"
CONFIG
chmod 600 "$state_dir/config.toml"
staged=$(mktemp "$bin_dir/.reason-network.XXXXXXXX")
trap 'rm -f "$staged"' EXIT
install -m 755 "$artifact_dir/reason-network" "$staged"
mv "$staged" "$binary"
cp "$artifact_dir/SOURCE_COMMIT" "$artifact_dir/SHA256SUMS" "$artifact_dir/RUST_VERSION" "$artifact_dir/LOCKFILE_SHA256" "$state_dir/"
"$binary" --version
"$binary" init dima-private --as dima --no-setup --json > "$state_dir/initial-team.json"
"$binary" setup --agent claude --agent codex --agent grok
"$binary" doctor

"$task_dir/venv/bin/python3" "$repo_dir/scripts/check-controlled-install.py" after
