"""Run the official tunnel client with a hidden runtime key, never saved to disk."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.request import build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tunnel-id', default=os.environ.get('CONTROL_PLANE_TUNNEL_ID'))
    parser.add_argument('--client', help='Path to the official tunnel-client.exe; otherwise use PATH')
    parser.add_argument('--mcp-port', type=int, default=3001)
    parser.add_argument('--health-port', type=int, default=8080)
    args = parser.parse_args()
    if not args.tunnel_id or not re.fullmatch(r'tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}', args.tunnel_id):
        raise SystemExit('Indicá --tunnel-id con el ID completo obtenido en Platform Tunnels; no es una clave secreta.')
    if any(not 1 <= value <= 65535 for value in (args.mcp_port, args.health_port)):
        raise SystemExit('Los puertos deben estar entre 1 y 65535.')
    client = args.client or shutil.which('tunnel-client')
    if not client or not Path(client).is_file():
        raise SystemExit('Falta tunnel-client. Descargá el binario oficial desde Platform Tunnels o github.com/openai/tunnel-client/releases/latest; indicá --client con su ruta.')
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{args.mcp_port}/healthz', timeout=5) as response:
            if json.load(response).get('service') != 'anime-data-agent-mcp':
                raise ValueError('Unexpected server')
    except (OSError, ValueError):
        raise SystemExit('Iniciá primero el servidor MCP local (npm.cmd --prefix apps/mcp start).') from None
    environment = os.environ.copy()
    key = environment.get('CONTROL_PLANE_API_KEY', '').strip()
    if not key:
        if not sys.stdin.isatty():
            raise SystemExit('Usá una terminal interactiva para ingresar la clave del túnel de forma oculta.')
        key = getpass.getpass('Clave runtime con Tunnels Read + Use (oculta, no se guarda): ').strip()
    if not key:
        raise SystemExit('No se ingresó clave; el MCP local continúa disponible sin túnel.')
    environment.update(CONTROL_PLANE_API_KEY=key, CONTROL_PLANE_TUNNEL_ID=args.tunnel_id,
                       MCP_SERVER_URL=f'http://127.0.0.1:{args.mcp_port}/mcp',
                       MCP_OAUTH_DISCOVERY='disabled', HEALTH_LISTEN_ADDR=f'127.0.0.1:{args.health_port}')
    print(f'Iniciando cliente oficial. Revisá http://127.0.0.1:{args.health_port}/ui y /readyz.')
    print('El proceso debe permanecer activo. La clave no se incluye en argumentos ni archivos del proyecto.')
    try:
        subprocess.run([str(Path(client).resolve()), 'run'], env=environment, check=True)
    except KeyboardInterrupt:
        pass
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit('El túnel terminó con error; revisá diagnóstico, permisos y asociación con tu cuenta de ChatGPT.') from None


if __name__ == '__main__':
    main()
