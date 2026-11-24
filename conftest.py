import os
import socket
import subprocess
import sys
import time
import httpx
import pytest

@pytest.fixture(scope="session")
def server(tmp_path_factory):
    root=tmp_path_factory.mktemp("doorlist")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    url=f"http://127.0.0.1:{port}"
    proc=subprocess.Popen([sys.executable,"-m","uvicorn","desk:app","--port",str(port),"--host","127.0.0.1"],
                          env={**os.environ,"DOORLIST_DB":str(root/"test.sqlite")})
    try:
        for _ in range(150):
            try:
                if httpx.get(url,timeout=1).status_code==200:
                    break
            except httpx.HTTPError:
                pass
            if proc.poll() is not None:
                raise RuntimeError("Fixture exited")
            time.sleep(.1)
        else:
            raise RuntimeError("Fixture did not become ready")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)
