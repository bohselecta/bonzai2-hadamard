#!/usr/bin/env python3
"""Failure-boundary checks for the Mac launcher; real inference evidence is separate."""
import hashlib
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mac_bonsai', ROOT / 'scripts/mac_bonsai.py')
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)


class LauncherChecks(unittest.TestCase):
    def test_same_size_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'models').mkdir()
            weights = root / 'models/model.gguf'
            original = b'GGUFverified weights'
            weights.write_bytes(original)
            model = {'file': weights.name, 'size': len(original),
                     'sha256': hashlib.sha256(original).hexdigest()}
            with patch.object(mac, 'ROOT', root), patch.object(mac, 'MODEL', model):
                self.assertEqual(mac.verify_weights(), weights)
                weights.write_bytes(b'X' * len(original))
                with self.assertRaisesRegex(RuntimeError, 'checksum changed'):
                    mac.verify_weights()
                self.assertEqual(weights.read_bytes(), b'X' * len(original))

    def test_occupied_port_does_not_spawn_or_stop_any_process(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]
            with patch.dict(mac.CONFIG, {'api_port': port}), patch.object(mac.subprocess, 'Popen') as spawn:
                with self.assertRaisesRegex(RuntimeError, 'occupied'):
                    mac.start_backend(None)
                spawn.assert_not_called()
                self.assertEqual(listener.getsockname()[1], port)

    def test_wrong_source_revision_preserves_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            marker = checkout / 'in-progress.txt'
            marker.write_text('preserve this work')
            with patch.object(mac.subprocess, 'check_output', return_value='different-head\n'), \
                    patch.object(mac, 'run') as mutate:
                with self.assertRaisesRegex(RuntimeError, 'unexpected revision'):
                    mac.clone('https://example.invalid/repo.git', 'required-head', checkout)
                mutate.assert_not_called()
                self.assertEqual(marker.read_text(), 'preserve this work')


if __name__ == '__main__':
    unittest.main(verbosity=2)
