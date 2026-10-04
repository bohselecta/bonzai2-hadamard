#!/usr/bin/env python3
"""Offline orchestration checks; these do not certify a GPU or submit a real PR."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


project = load("project")
publisher = load("submit_pr")


class ProjectChecks(unittest.TestCase):
    def test_failed_verification_does_not_enable_server(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(workspace=Path(directory), backend="cuda", jobs=4, context=2048, threads=4)
            calls = []

            def fail_verify(command, env):
                calls.append([str(x) for x in command])
                if str(command[1]).endswith("verify_model.py"):
                    raise RuntimeError("actual-model verification failed")

            with patch.object(project, "preflight", return_value={"CUDA_VISIBLE_DEVICES": "0"}), \
                    patch.object(project, "run", side_effect=fail_verify):
                with self.assertRaisesRegex(RuntimeError, "verification failed"):
                    project.setup(args)
            self.assertEqual(len(calls), 3)
            self.assertIn("cuda", calls[0])
            self.assertIn("cuda", calls[2])
            self.assertFalse((args.workspace / "project-state.json").exists())

    def test_serve_uses_verified_device_and_loopback(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            model = workspace / "model.gguf"
            model.write_bytes(b"fixture")
            manifest = {"size": 7, "sha256": hashlib.sha256(b"fixture").hexdigest()}
            state = {"binary": "/fixture/llama-server", "model": str(model), "backend": "cuda",
                     "context": 2048, "threads": 4, "cuda_visible_devices": "2"}
            (workspace / "project-state.json").write_text(json.dumps(state))
            with patch.object(project, "MODEL", manifest), patch.object(project.os, "execvpe") as execute:
                project.serve(SimpleNamespace(workspace=workspace, port=8080))
            _, command, env = execute.call_args.args
            for flag, value in [("--host", "127.0.0.1"), ("--alias", "bonsai2"),
                                ("--device", "CUDA0"), ("-ngl", "99"), ("-b", "128"), ("-ub", "32")]:
                self.assertEqual(command[command.index(flag) + 1], value)
            self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "2")
            model.write_bytes(b"changed")
            with patch.object(project, "MODEL", manifest), patch.object(project.os, "execvpe") as execute:
                with self.assertRaisesRegex(RuntimeError, "Checkpoint changed"):
                    project.serve(SimpleNamespace(workspace=workspace, port=8080))
                execute.assert_not_called()

    def test_missing_cuda_toolchain_stops_before_build(self):
        with patch.object(project.shutil, "which", side_effect=lambda name: None if name == "nvcc" else "/tool"), \
                patch.object(project, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "nvcc"):
                project.preflight("cuda", Path(tempfile.gettempdir()))
            run.assert_not_called()


class PublisherChecks(unittest.TestCase):
    def setUp(self):
        identity = {"GIT_AUTHOR_NAME": "Bonsai test", "GIT_AUTHOR_EMAIL": "bonsai-test@example.invalid",
                    "GIT_COMMITTER_NAME": "Bonsai test", "GIT_COMMITTER_EMAIL": "bonsai-test@example.invalid",
                    "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "Bonsai test",
                    "GIT_CONFIG_KEY_1": "user.email", "GIT_CONFIG_VALUE_1": "bonsai-test@example.invalid"}
        self.identity = patch.dict(os.environ, identity)
        self.identity.start()
        self.addCleanup(self.identity.stop)

    def test_real_git_preparation_preserves_patches_and_rejects_dirty_work(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "prepared"
            state, _ = publisher.prepare(destination)
            changed = subprocess.check_output(["git", "diff", "--name-only", "main..." + publisher.BRANCH],
                                              cwd=destination, text=True).splitlines()
            self.assertIn("patches/bonsai2-combined.patch", changed)
            self.assertIn("CODEX_UBUNTU_TASK.md", changed)
            self.assertEqual((destination / "patches/bonsai2-combined.patch").read_bytes(),
                             (ROOT / "patches/bonsai2-combined.patch").read_bytes())
            again, _ = publisher.prepare(destination)
            self.assertEqual(state, again)
            (destination / "README.md").write_text("Existing user's work\n")
            with self.assertRaisesRegex(RuntimeError, "uncommitted work"):
                publisher.prepare(destination)
            self.assertEqual((destination / "README.md").read_text(), "Existing user's work\n")

    def test_wrong_account_never_creates_repository(self):
        with patch.object(publisher.shutil, "which", return_value="/gh"), \
                patch.object(publisher, "command", return_value="another-account") as command:
            with self.assertRaisesRegex(RuntimeError, "authenticated as another-account"):
                publisher.publish(SimpleNamespace(owner="bohselecta", name="bonsai2-hadamard"), {}, Path("unused"))
            self.assertEqual(command.call_count, 1)

    def test_publication_order_and_retry_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            state_path = destination / "state.json"
            (destination / ".git").mkdir()
            args = SimpleNamespace(directory=destination, owner="bohselecta", name="bonsai2-hadamard")
            repo = "bohselecta/bonsai2-hadamard"
            url = "https://github.com/" + repo + "/pull/123"
            calls = []
            remote_created = False
            opened = False

            def fake(command, cwd=None, capture=False):
                nonlocal remote_created, opened
                command = [str(x) for x in command]
                calls.append(command)
                if command[:2] == ["gh", "api"]:
                    if "user" in command:
                        return "bohselecta"
                    return json.dumps({"private": True, "owner": {"login": "bohselecta"}})
                if command[:3] == ["gh", "repo", "create"]:
                    self.assertFalse(remote_created)
                    self.assertIn("--private", command)
                    remote_created = True
                if command[:3] == ["git", "remote", "get-url"]:
                    return "https://github.com/" + repo + ".git"
                if "push" in command:
                    self.assertTrue(remote_created)
                    self.assertIn("main:main", command)
                    self.assertIn(publisher.BRANCH + ":" + publisher.BRANCH, command)
                if command[:3] == ["gh", "pr", "list"]:
                    return json.dumps([{"url": url}] if opened else [])
                if command[:3] == ["gh", "pr", "create"]:
                    self.assertIn("--draft", command)
                    self.assertIn("--body-file", command)
                    self.assertTrue(any("push" in prior for prior in calls[:-1]))
                    opened = True
                    return url
                return ""

            state = {}
            with patch.object(publisher.shutil, "which", return_value="/gh"), \
                    patch.object(publisher, "command", side_effect=fake), \
                    patch("sys.stdout", new_callable=io.StringIO):
                publisher.publish(args, state, state_path)
                publisher.publish(args, state, state_path)
            self.assertEqual(state["pull_request"], url)
            self.assertEqual(sum(c[:3] == ["gh", "repo", "create"] for c in calls), 1)
            self.assertEqual(sum(c[:3] == ["gh", "pr", "create"] for c in calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
