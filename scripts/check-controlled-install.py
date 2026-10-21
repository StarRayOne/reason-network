import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
import tomllib

root = Path(__file__).resolve().parents[1] / '.build'
user_dir = Path.home()
snapshot = root / 'settings-before.json'

def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def settings_fingerprints():
    values = {}
    for agent in ('codex', 'grok'):
        cfg = tomllib.loads((user_dir / f'.{agent}/config.toml').read_text())
        cfg.get('mcp_servers', {}).pop('reason-network', None)
        if not cfg.get('mcp_servers'):
            cfg.pop('mcp_servers', None)
        values[agent] = digest(cfg)
    values['claude_permissions'] = digest(json.loads((user_dir / '.claude/settings.json').read_text()))
    return values

if sys.argv[1] == 'before':
    snapshot.write_text(json.dumps(settings_fingerprints()))
    snapshot.chmod(0o600)
    print('Saved configuration fingerprints; no credential contents recorded.')
    sys.exit(0)

assert settings_fingerprints() == json.loads(snapshot.read_text()), 'Settings outside the new MCP entries changed'
binary = user_dir / '.local/bin/reason-network'
state = user_dir / '.reason/network'
assert stat.S_IMODE(state.stat().st_mode) == 0o700 and state.stat().st_uid == os.getuid()
cfg = tomllib.loads((state / 'config.toml').read_text())
assert cfg['inbound']['default'] == 'hold' and not cfg.get('inbound', {}).get('people')
assert not any(cfg[key] for key in ('auto_update', 'share_paths', 'share_unmanaged', 'lan', 'reason'))
for agent in ('codex', 'grok'):
    cfg = tomllib.loads((user_dir / f'.{agent}/config.toml').read_text())
    server = cfg['mcp_servers']['reason-network']
    assert server['command'] == str(binary) and server['args'] == ['mcp']
    assert 'default_tools_approval_mode' not in server
claude = json.loads((user_dir / '.claude.json').read_text())['mcpServers']['reason-network']
assert claude['command'] == str(binary) and claude['args'] == ['mcp']
assert 'reason-network' in (user_dir / '.codex/hooks.json').read_text()
assert 'reason-network' in (user_dir / '.grok/hooks/reason-network.json').read_text()
plist_path = user_dir / 'Library/LaunchAgents/com.reasonmachines.network.plist'
plist = plistlib.loads(plist_path.read_bytes())
assert plist['ProgramArguments'][0] == str(binary)
assert plist['RunAtLoad'] and plist['KeepAlive']
service = subprocess.run(['launchctl', 'print', f'gui/{os.getuid()}/com.reasonmachines.network'], capture_output=True, text=True, check=True)
assert re.search(r'\bstate = running\b', service.stdout), 'Service not running'
actual = hashlib.sha256(binary.read_bytes()).hexdigest()
expected = (root / 'artifact/SHA256SUMS').read_text().split()[0]
assert actual == expected
for name in ('config.toml', 'machine.key', 'network.db', 'initial-team.json'):
    path = state / name
    assert path.exists() and stat.S_IMODE(path.stat().st_mode) == 0o600, name
print(json.dumps({'installed':str(binary),'service':'running','agents':['claude','codex','grok'],
                  'existing_settings':'preserved','inbound':'hold','state_mode':'0700','sha256':actual}))
