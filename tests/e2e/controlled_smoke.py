import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[2] / '.build'
binary = root / 'artifact' / 'reason-network'
state = Path(tempfile.mkdtemp(prefix='controlled-smoke-', dir=root))
state.chmod(0o700)
(state / 'config.toml').write_text('person="smoke"\nlan=false\ntray=false\nauto_update=false\nshare_unmanaged=false\nreason=false\n[inbound]\ndefault="hold"\n')
env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'REASON_NETWORK_HOME': str(state),
       'REASON_NETWORK_NO_SERVICE': '1', 'REASON_NETWORK_NO_TRAY': '1',
       'REASON_NETWORK_NO_MDNS': '1', 'REASON_NETWORK_MACHINE': 'smoke',
       'CLAUDE_CONFIG_DIR': str(root / 'smoke-claude')}

def cli(*args, check=True):
    result = subprocess.run([str(binary), *args], env=env, capture_output=True, text=True, timeout=40)
    if check and result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr or result.stdout}')
    return result

process = None
receiver = None
try:
    assert '0.12.3-controlled.1' in cli('--version').stdout
    denied = cli('upgrade', check=False)
    assert denied.returncode != 0 and 'binary replacement is disabled' in denied.stderr
    created = json.loads(cli('init', 'smoke-private', '--as', 'smoke', '--no-setup', '--json').stdout)
    assert created['person'] == 'smoke'
    receiver = subprocess.Popen([str(binary), 'listen', '--as', 'check', '--wait', '20'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Wait on observable registration, not an assumed startup delay.
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if 'smoke/check' in cli('who', '--json').stdout:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError('smoke receiver did not register')
    cli('send', 'smoke/check', '--fyi', 'controlled-install-smoke')
    output, errors = receiver.communicate(timeout=15)
    assert receiver.returncode == 0 and 'controlled-install-smoke' in output, errors
    process = subprocess.Popen([str(binary), 'mcp'], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    def rpc(request, expected):
        process.stdin.write(json.dumps(request) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if not select.select([process.stdout], [], [], 1)[0]:
                continue
            line = process.stdout.readline()
            if not line:
                raise RuntimeError('MCP exited before responding')
            response = json.loads(line)
            if response.get('id') == expected:
                assert 'error' not in response, response
                return response['result']
        raise TimeoutError('MCP response timed out')

    initialized = rpc({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'controlled-smoke','version':'1'}}}, 1)
    process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'}) + '\n')
    process.stdin.flush()
    listed = rpc({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}, 2)
    names = sorted(tool['name'] for tool in listed['tools'])
    assert {'list_team','send_message','check_inbox','ask_user'}.issubset(names), names
    print(json.dumps({'version':initialized['serverInfo']['version'],'local_message':'passed','mcp_tools':names,'upstream_upgrade':'disabled','team_link':'kept private'}))
finally:
    for proc in (process, receiver):
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    cli('stop', check=False)
