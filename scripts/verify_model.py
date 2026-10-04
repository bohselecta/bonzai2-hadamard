#!/usr/bin/env python3
"""Run the pinned real model through a loopback server and save the results."""
import argparse
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from download_model import digest

ROOT = Path(__file__).resolve().parents[1]
ARCHITECT_PROMPT = "Write a prompt for an LLM to use for a System Prompt: Systems Architect (Cross-Platform Unification) including its Role & Mission, and Core Directives."


def request(url, body=None, timeout=15):
    encoded = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=encoded, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--backend", choices=("cpu", "cuda", "metal"), default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--architect", action="store_true", help="also run the exact Systems Architect prompt")
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    binary, model = args.binary.expanduser().resolve(), args.model.expanduser().resolve()
    if not binary.is_file() or not model.is_file():
        raise RuntimeError("Server binary and model must exist")
    meta = json.loads((ROOT / "model.json").read_text())
    if model.stat().st_size != meta["size"]:
        raise RuntimeError("Expected the pinned Q2_0 file; do not use fork-specific PQ2_0/PTQ1_0 files")
    print("Verifying the pinned model checksum...", flush=True)
    if digest(model) != meta["sha256"]:
        raise RuntimeError("Model checksum differs from the pinned Q2_0 checkpoint")
    if args.context < 1024 or args.threads < 1:
        raise RuntimeError("Use at least 1024 context and one CPU thread")
    output = args.output.expanduser().resolve()
    if output.exists():
        raise RuntimeError("Output directory already exists; previous evidence was preserved")
    output.mkdir(parents=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    command = [str(binary), "-m", str(model), "--host", "127.0.0.1", "--port", str(port),
               "--alias", "bonsai2", "-ngl", "0" if args.backend == "cpu" else "99",
               "-np", "1", "-c", str(args.context), "-b", "128", "-ub", "32",
               "-t", str(args.threads), "-lv", "4", "--fit", "off", "--jinja",
               "--reasoning", "off", "--reasoning-budget", "0"]
    if args.backend != "cpu":
        command += ["--device", "CUDA0" if args.backend == "cuda" else "MTL0"]
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (output / "server.log").open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        base = f"http://127.0.0.1:{port}"
        try:
            start = time.monotonic()
            print("Loading model on the requested backend...", flush=True)
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Server exited during load; see server.log")
                try:
                    if request(base + "/health").get("status") == "ok":
                        break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    pass
                if time.monotonic() - start > 600:
                    raise RuntimeError("Server readiness timed out; see server.log")
                time.sleep(0.5)
            props = request(base + "/props")
            (output / "props.json").write_text(json.dumps(props, indent=2) + "\n")
            text = (output / "server.log").read_text(errors="replace")
            if "Hadamard-folded weight(s)" not in text:
                raise RuntimeError("No Hadamard transform load record was found")
            if args.backend == "cuda" and "CUDA0" not in text:
                raise RuntimeError("CUDA device was not found in the server log")
            if args.backend == "metal" and not any(word in text for word in ("Metal", "MTL", "metal")):
                raise RuntimeError("Metal device was not found in the server log")
            if args.backend != "cpu":
                offload = re.search(r"offloaded (\d+)/(\d+) layers to GPU", text)
                if not offload or int(offload[1]) == 0 or offload[1] != offload[2]:
                    raise RuntimeError("Full GPU layer offload was not confirmed; inspect server.log")

            cases = [("marker", "Return exactly BONSAI_OK, without any explanation.", None, "BONSAI_OK"),
                     ("json-arithmetic", "Calculate 17 + 26. Return a JSON object with its integer sum.",
                      {"type": "json_schema", "json_schema": {"name": "sum", "strict": True,
                       "schema": {"type": "object", "properties": {"sum": {"type": "integer"}},
                                  "required": ["sum"], "additionalProperties": False}}}, {"sum": 43})]
            if args.architect:
                cases.append(("systems-architect", ARCHITECT_PROMPT, None, None))
            results = []
            for name, prompt, format_, expected in cases:
                print(f"Running {name}...", flush=True)
                body = {"model": "bonsai2", "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0, "seed": 42, "max_tokens": 1024 if expected is None else 128,
                        "cache_prompt": False}
                if format_:
                    body["response_format"] = format_
                (output / f"{name}-request.json").write_text(json.dumps(body, indent=2) + "\n")
                begin = time.monotonic()
                response = request(base + "/v1/chat/completions", body, timeout=900)
                (output / f"{name}-response.json").write_text(json.dumps(response, indent=2) + "\n")
                choice = response["choices"][0]
                answer = choice["message"].get("content", "")
                (output / f"{name}.txt").write_text(answer + "\n")
                ok = answer.strip() == expected if isinstance(expected, str) else json.loads(answer) == expected if expected is not None else bool(answer.strip())
                if choice.get("finish_reason") == "length":
                    ok = False
                result = {"case": name, "passed": ok, "seconds": time.monotonic() - begin,
                          "usage": response.get("usage"), "timings": response.get("timings"),
                          "finish_reason": choice.get("finish_reason")}
                results.append(result)
                (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
                if not ok:
                    raise RuntimeError(f"{name} did not satisfy its check; raw output retained")
                print(f"PASS {name}", flush=True)
            print(f"Real-model checks passed; evidence: {output}")
            if args.architect:
                print("The architect answer still needs a human quality review.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
