"""Run local phase 8 checks without model calls; preserve reviewable evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--http', action='store_true', help='Also check an already running API in rules mode')
    parser.add_argument('--mcp', action='store_true', help='Also build and test the Node MCP package (no model calls)')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'docs/evidence/phase8' / stamp
    output.mkdir(parents=True)
    environment = os.environ.copy()
    environment.pop('OPENAI_API_KEY', None)
    environment.update(ANIME_AGENT_MODE='rules', ANIME_HTTP_TESTS='0', PYTHONUTF8='1', NEXT_TELEMETRY_DISABLED='1')
    npm = shutil.which('npm.cmd') or shutil.which('npm') or 'npm'
    node = shutil.which('node') or 'node'
    checks = [
        ('dependencies', [sys.executable, '-m', 'pip', 'check']),
        ('dataset_tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_prepare_dataset.py', '-v']),
        ('backend_tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'apps/api/tests', '-v']),
        ('acceptance', [sys.executable, 'scripts/check_acceptance.py']),
        ('conversation_demo', [sys.executable, 'scripts/demo_local.py']),
        ('artwork_tests', [node, '--experimental-strip-types', '--test', 'apps/web/tests/artwork.test.mjs']),
        ('typecheck', [npm, '--prefix', 'apps/web', 'run', 'typecheck']),
        ('web_build', [npm, '--prefix', 'apps/web', 'run', 'build']),
    ]
    if args.http:
        checks.append(('http', [sys.executable, 'scripts/smoke_api.py']))
    if args.mcp:
        checks.append(('mcp_tests', [npm, '--prefix', 'apps/mcp', 'test']))
    results = []
    for name, command in checks:
        print(f'Checking {name}...', flush=True)
        start = time.monotonic()
        try:
            completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                                       encoding='utf-8', errors='replace', timeout=240)
            code, log = completed.returncode, completed.stdout + completed.stderr
        except (OSError, subprocess.TimeoutExpired) as error:
            code, log = -1, str(error)
        (output / f'{name}.txt').write_text(log, encoding='utf-8')
        results.append(dict(check=name, exit_code=code, seconds=round(time.monotonic()-start, 2), log=f'{name}.txt'))
        print(f'{name}: {"PASS" if code == 0 else "FAIL"}', flush=True)
    report = dict(created_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                  status='local_checks_passed' if all(r['exit_code'] == 0 for r in results) else 'checks_failed',
                  checks=results, http='executed' if args.http else 'not_executed',
                  limitations=['OpenAI real: pending; user reported credit_balance_exhausted.',
                               'ASGI case omitted by default; inspect backend log.',
                               'No automated browser or fresh-machine installation verification.',
                               'Artwork tests mock the remote provider; no live availability guarantee.'])
    (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output.parent / 'latest.json').write_text(json.dumps({'report': f'{stamp}/summary.json'}, indent=2), encoding='utf-8')
    print(f'Evidence: {output.relative_to(ROOT)}')
    return 0 if report['status'] == 'local_checks_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
