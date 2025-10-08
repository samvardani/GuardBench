import os
import time
import subprocess
import sys
import socket
import pytest


def wait_port(host: str, port: int, timeout: float = 5.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket() as s:
            s.settimeout(0.25)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    return False


@pytest.mark.timeout(10)
def test_grpc_smoke() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    srv = subprocess.Popen([sys.executable, "src/grpc/server.py"], env=env)
    try:
        assert wait_port("127.0.0.1", 50051, 5), "gRPC server didn’t open :50051"
        code = r'''
import os, sys
sys.path.insert(0, os.getcwd())
from grpc import insecure_channel  # type: ignore
from src.grpc_generated import score_pb2, score_pb2_grpc  # type: ignore

with insecure_channel("127.0.0.1:50051") as ch:
    stub = score_pb2_grpc.ScoreServiceStub(ch)
    resp = stub.Score(score_pb2.ScoreRequest(text="hello", category="violence", language="en"), timeout=2.0)
    print(resp.score)
'''
        p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=5)
        assert p.returncode == 0, p.stderr
        float(p.stdout.strip())
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=3)
        except Exception:
            srv.kill()

