"""Start local API with a hidden API-key prompt; never writes credentials to disk."""
import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['openai', 'rules'], default='openai')
    parser.add_argument('--model', default=os.environ.get('OPENAI_MODEL', 'gpt-5-mini'))
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit('Puerto inválido.')
    environment = os.environ.copy()
    environment['ANIME_AGENT_MODE'] = args.mode
    environment['OPENAI_MODEL'] = args.model
    if args.mode == 'openai' and not environment.get('OPENAI_API_KEY'):
        value = getpass.getpass('Clave de OpenAI API (Enter para continuar sin IA, no se guarda): ').strip() if sys.stdin.isatty() else ''
        if value:
            environment['OPENAI_API_KEY'] = value
        else:
            print('ADVERTENCIA: no se inició la conexión con IA. Se continuará con reglas locales.')
    print(f'API local · modo {args.mode} · modelo {args.model if args.mode == "openai" else "sin modelo"}')
    print('Crear servidor no consume API; los mensajes en modo openai sí pueden generar consumo.')
    try:
        subprocess.run([sys.executable, '-m', 'uvicorn', 'anime_agent.main:app', '--host', '127.0.0.1', '--port', str(args.port)],
                       cwd=Path(__file__).resolve().parents[1], env=environment, check=True)
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError:
        raise SystemExit('La API terminó con error; revisá el mensaje del servidor.') from None


if __name__ == '__main__':
    main()
