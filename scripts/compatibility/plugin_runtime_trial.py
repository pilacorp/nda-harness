#!/usr/bin/env python3
"""Isolated Codex native package discovery; no model, login or memory operations.

The host keychain may already contain native credentials for the packaged URL.
Only the host runtime uses them; this probe never reads or exports credentials.
"""
import argparse
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import time


class NativeRuntime:
    def __init__(self, executable, env, cwd):
        self.process = subprocess.Popen([executable, 'app-server', '--stdio'], cwd=cwd, env=env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b''
        self.sequence = 0

    def request(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                message = json.loads(line)
                if message.get('id') == request_id:
                    if 'error' in message:
                        raise RuntimeError('Native request failed: ' + method + ' (code ' + str(message['error'].get('code')) + ')')
                    return message['result']
            if self.selector.select(timeout=1):
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('Native runtime exited before response.')
                self.buffer += chunk
        raise TimeoutError('Native request timed out: ' + method)

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + '\n').encode())
        self.process.stdin.flush()

    def close(self):
        self.selector.close()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


def trial(executable, package):
    with tempfile.TemporaryDirectory(prefix='nda-native-plugin-') as directory:
        root = Path(directory).resolve()
        home = root / 'codex-home'
        home.mkdir(mode=0o700)
        project = root / 'project'
        project.mkdir()
        env = {**os.environ, 'CODEX_HOME': str(home)}
        subprocess.run(['git', 'init', '-q', str(project)], capture_output=True, check=True)
        version = subprocess.run([executable, '--version'], capture_output=True, text=True, check=True).stdout.strip()
        for args in (['plugin', 'marketplace', 'add', str(package), '--json'],
                     ['plugin', 'add', 'nda-harness@nda-harness-local', '--json']):
            run = subprocess.run([executable, *args], env=env, cwd=project, capture_output=True, text=True, timeout=40)
            if run.returncode:
                raise RuntimeError('Native package registration failed.')
            registration = json.loads(run.stdout)
        runtime = NativeRuntime(executable, env, project)
        try:
            runtime.request('initialize', {'clientInfo': {'name': 'nda_plugin_trial', 'version': '0.0.0'}, 'capabilities': {'experimentalApi': True}})
            runtime.send({'method': 'initialized', 'params': {}})
            detail = runtime.request('plugin/read', {'pluginName': 'nda-harness', 'marketplacePath': str(package / '.agents/plugins/marketplace.json')})['plugin']
            hooks = runtime.request('hooks/list', {'cwds': [str(project)]})['data']
            skills = runtime.request('skills/list', {'cwds': [str(project)], 'forceReload': True})['data']
            result = {'runtime': version, 'auth_policy': registration.get('authPolicy'),
                      'plugin_skill_count': len(detail.get('skills', [])), 'plugin_mcp_servers': detail.get('mcpServers', []),
                      'hook_events': sorted({h['eventName'] for entry in hooks for h in entry.get('hooks', []) if h.get('pluginId') == 'nda-harness@nda-harness-local'}),
                      'hook_trust': sorted({h['trustStatus'] for entry in hooks for h in entry.get('hooks', []) if h.get('pluginId') == 'nda-harness@nda-harness-local'}),
                      'hook_error_count': sum(len(entry.get('errors', [])) for entry in hooks),
                      'skill_error_count': sum(len(entry.get('errors', [])) for entry in skills),
                      'discovered_plugin_skills': sorted({s['name'] for entry in skills for s in entry.get('skills', []) if s.get('pluginId') == 'nda-harness@nda-harness-local'}),
                      'model_invoked': False, 'memory_operations': False, 'hook_execution': 'not_attempted_trust_required'}
            for name in detail.get('mcpServers', []):
                if re.fullmatch(r'[a-zA-Z0-9_:@/.-]+', name) is None:
                    raise RuntimeError('Native MCP identifier is invalid: ' + name)
            memory_server = 'nda-harness-hindsight'
            if memory_server in detail.get('mcpServers', []):
                discovered = runtime.request('mcpServerStatus/list', {'serverName': memory_server, 'detail': 'toolsAndAuthOnly'})
                server = next((s for s in discovered.get('data', []) if s.get('name') == memory_server), {})
                tools = sorted(server.get('tools', {}))
                result['memory_discovery'] = {'auth_status': server.get('authStatus'), 'tool_count': len(tools),
                                              'tools': tools, 'required_tools_available': {'list_banks', 'create_bank', 'recall', 'retain'} <= set(tools)}
            expected = {'session-bootstrap', 'task-prepare', 'context-refresh', 'context-checkpoint', 'context-resume',
                        'nda-setup', 'nda-verify', 'hindsight-memory', 'test-driven-development', 'using-superpowers'}
            names = {name.split(':')[-1] for name in result['discovered_plugin_skills']}
            result['package_discovery_passed'] = (result['auth_policy'] == 'ON_USE' and expected <= names
                and result['hook_events'] == ['preCompact', 'sessionStart', 'userPromptSubmit']
                and result['hook_error_count'] == 0 and result['skill_error_count'] == 0)
            return result
        finally:
            runtime.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', required=True, help='Absolute path to the installed Desktop runtime')
    parser.add_argument('--package', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = trial(args.codex, args.package.resolve())
        print(json.dumps(result, indent=2))
        return 0 if result['package_discovery_passed'] else 1
    except RuntimeError as error:
        print(json.dumps({'status': 'failed', 'detail': str(error)}))
        return 1
    except (OSError, ValueError, TimeoutError, subprocess.SubprocessError):
        print(json.dumps({'status': 'failed', 'detail': 'Native registration/discovery failed; no raw output retained.'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
