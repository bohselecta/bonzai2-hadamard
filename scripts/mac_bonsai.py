#!/usr/bin/env python3
"""Build and run the isolated, pinned Bonsai Ollama client on Apple Silicon."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'mac-runtime.json').read_text())
MODEL = json.loads((ROOT / 'evidence/mac/model.json').read_text())
STATE = ROOT / '.state'
OLLAMA = ROOT / 'runtime/ollama-prism'
LLAMA = ROOT / 'runtime/prism-llama'
BUILD = OLLAMA / 'build-mac'
BINARY = BUILD / 'bin/ollama'
API = f"http://127.0.0.1:{CONFIG['api_port']}"


def run(command, cwd=ROOT):
    subprocess.run([str(x) for x in command], cwd=cwd, check=True)


def environment():
    env = os.environ.copy()
    env.update(OLLAMA_HOST=f"127.0.0.1:{CONFIG['api_port']}", OLLAMA_MODELS=str(STATE / 'models'),
               OLLAMA_NO_CLOUD='1', OLLAMA_CONTEXT_LENGTH='2048', OLLAMA_NUM_PARALLEL='1',
               OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_FLASH_ATTENTION='1',
               LLAMA_ARG_CACHE_RAM='128', LLAMA_ARG_CTX_CHECKPOINTS='1')
    return env


def clone(url, revision, destination):
    if not destination.exists():
        run(['git', 'clone', '--filter=blob:none', '--no-checkout', url, destination])
        run(['git', 'checkout', '--detach', revision], destination)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=destination, text=True).strip()
    if actual != revision:
        raise RuntimeError(f'{destination}: unexpected revision {actual}; checkout preserved')


def build():
    clone(CONFIG['ollama_repository'], CONFIG['ollama_revision'], OLLAMA)
    clone(CONFIG['llama_repository'], CONFIG['llama_revision'], LLAMA)
    exclude = OLLAMA / '.git/info/exclude'
    if '/build-mac/' not in exclude.read_text():
        with exclude.open('a') as output:
            output.write('\n/build-mac/\n')
    patch = ROOT / 'patches/mac-ollama-file-types.patch'
    applied = subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=OLLAMA,
                             capture_output=True).returncode == 0
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=OLLAMA, text=True)
    allowed = {'fs/gguf/file_type.go', 'fs/gguf/gguf_internal_test.go'}
    if dirty and (not applied or any(line[3:] not in allowed for line in dirty.splitlines())):
        raise RuntimeError('Ollama source contains other work; preserved')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=LLAMA, text=True).strip():
        raise RuntimeError('Prism source contains other work; preserved')
    if not applied:
        run(['git', 'apply', '--check', patch], OLLAMA)
        run(['git', 'apply', patch], OLLAMA)
    run(['cmake', '-S', OLLAMA, '-B', BUILD, '-DOLLAMA_MLX_BACKENDS=', '-DOLLAMA_LLAMA_BACKENDS=',
         f'-DFETCHCONTENT_SOURCE_DIR_LLAMA_CPP={LLAMA}', f"-DOLLAMA_VERSION={CONFIG['version']}",
         f'-DOLLAMA_GO_OUTPUT={BINARY}', '-DOLLAMA_BUILD_PARALLEL=4'])
    run(['cmake', '--build', BUILD, '--target', 'ollama-local', '--parallel', '4'])
    run(['go', 'test', './fs/gguf', './llm'], OLLAMA)


def verify_weights():
    path = ROOT / 'models' / MODEL['file']
    if not path.exists() or path.stat().st_size != MODEL['size']:
        raise RuntimeError('Verified model is missing or its size changed')
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != MODEL['sha256']:
        raise RuntimeError('Model checksum changed; refusing to load')
    return path


def available(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) != 0


def stop_backend(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    # A crashed daemon may leave its runner in the same process group.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def start_backend(log):
    if not available(CONFIG['api_port']):
        raise RuntimeError(f"Port {CONFIG['api_port']} is occupied; its process was left untouched")
    process = subprocess.Popen([str(BINARY), 'serve'], cwd=ROOT, env=environment(),
                               stdout=log, stderr=log, start_new_session=True)
    (STATE / 'backend.json').write_text(json.dumps({'pid': process.pid, 'binary': str(BINARY)}) + '\n')
    return process


def wait_backend(process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('Ollama exited; see .state/ollama.log')
        try:
            with urllib.request.urlopen(API + '/api/version', timeout=1) as response:
                json.load(response)
                return
        except OSError:
            time.sleep(.1)
    raise RuntimeError('Ollama startup timed out; see .state/ollama.log')


def setup():
    if not BINARY.is_file():
        build()
    path = verify_weights()
    blobs = STATE / 'models/blobs'
    blobs.mkdir(parents=True, exist_ok=True)
    blob = blobs / ('sha256-' + MODEL['sha256'])
    if not blob.exists():
        os.link(path, blob)
    elif not os.path.samefile(path, blob):
        raise RuntimeError('Existing model blob is not the verified hardlink; preserved')
    modelfile = STATE / 'Modelfile'
    modelfile.write_text(f'''FROM {path}
PARAMETER num_ctx 2048
PARAMETER num_batch 128
PARAMETER num_gpu 99
PARAMETER num_thread 4
PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 20
PARAMETER min_p 0
PARAMETER repeat_penalty 1
PARAMETER presence_penalty 1.5
SYSTEM You are a helpful assistant.
''')
    with (STATE / 'ollama.log').open('ab', buffering=0) as log:
        process = start_backend(log)
        try:
            wait_backend(process)
            subprocess.run([str(BINARY), 'create', CONFIG['model_name'], '-f', str(modelfile)],
                           env=environment(), check=True)
        finally:
            stop_backend(process)
    print('Setup complete. Run: python3 scripts/mac_bonsai.py run')


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in (f"127.0.0.1:{CONFIG['client_port']}", f"localhost:{CONFIG['client_port']}"):
            self.send_error(403)
            return
        if self.path not in ('/', '/index.html'):
            self.send_error(404)
            return
        body = (ROOT / 'client/index.html').read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src http://127.0.0.1:11435; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def serve(open_browser):
    if not BINARY.is_file():
        raise RuntimeError('Run setup first')
    verify_weights()
    data = json.loads((STATE / 'models/manifests/registry.ollama.ai/library/bonsai2/ptq1').read_text())
    if not any(layer['digest'] == 'sha256:' + MODEL['sha256'] for layer in data['layers']):
        raise RuntimeError('Installed model identity changed; run setup')
    server = ThreadingHTTPServer(('127.0.0.1', CONFIG['client_port']), Page)
    server.daemon_threads = True
    quit_event = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: quit_event.set())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{CONFIG['client_port']}"
    with (STATE / 'ollama.log').open('ab', buffering=0) as log:
        process = None
        try:
            process = start_backend(log)
            wait_backend(process)
            print(f'Bonsai: {url}\nClose this terminal or press Ctrl+C to stop.', flush=True)
            if open_browser:
                webbrowser.open(url)
            while not quit_event.wait(1):
                if process.poll() is not None:
                    print('Backend exited; cleaning runner and restarting.', flush=True)
                    stop_backend(process)
                    process = None
                    if quit_event.wait(1):
                        break
                    process = start_backend(log)
                    wait_backend(process)
        finally:
            if process is not None:
                stop_backend(process)
            server.shutdown()
            server.server_close()
            (STATE / 'backend.json').unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'setup', 'run', 'stop'])
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.uname().machine != 'arm64':
        parser.error('This launcher requires an Apple Silicon Mac')
    STATE.mkdir(exist_ok=True)
    with (STATE / 'launcher.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if args.action == 'stop':
                pid = int((STATE / 'launcher.pid').read_text())
                command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'args='], text=True)
                owner = int(subprocess.check_output(['ps', '-p', str(pid), '-o', 'uid='], text=True))
                if 'mac_bonsai.py run' not in command or owner != os.getuid():
                    raise RuntimeError('Launcher identity differs; process was preserved')
                os.kill(pid, signal.SIGTERM)
                for _ in range(150):
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        print('Bonsai stopped.')
                        return
                    except BlockingIOError:
                        time.sleep(.1)
                raise RuntimeError('Shutdown still in progress; inspect the launcher terminal')
            if args.action == 'run' and not args.no_browser:
                webbrowser.open(f"http://127.0.0.1:{CONFIG['client_port']}")
                print('Opened the running Bonsai client.')
                return
            raise RuntimeError('Bonsai is already running; use the existing window')
        if args.action == 'stop':
            print('Bonsai is already stopped.')
            return
        (STATE / 'launcher.pid').write_text(str(os.getpid()) + '\n')
        if args.action == 'build':
            build()
        elif args.action == 'setup':
            setup()
        else:
            serve(not args.no_browser)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
