"""Dense STL work must not occupy the API event loop."""
import asyncio
import threading

import httpx


def test_dense_upload_leaves_api_responsive(monkeypatch):
    from backend.app import app
    entered, release = threading.Event(), threading.Event()
    def reduction(*args):
        entered.set()
        assert release.wait(2), 'Upload blocked the event loop'
        return {'id': 'test'}
    monkeypatch.setattr('backend.stl_io.store_stl', reduction)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver') as client:
            upload = asyncio.create_task(client.post('/api/stls', content=b'test'))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                response = await asyncio.wait_for(client.get('/api/health'), timeout=1)
                assert response.status_code == 200
            finally:
                release.set()
            assert (await upload).status_code == 200
    asyncio.run(exercise())
