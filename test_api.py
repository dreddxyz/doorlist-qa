from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import httpx

def venue(server,cap):
    r=httpx.post(server+"/shows",json={"capacity":cap})
    r.raise_for_status()
    return server+"/shows/"+r.json()["id"]

def order(url,qty=1,key=None):
    return httpx.post(url+"/tickets",json={"qty":qty,"request_id":key or str(uuid4())})

def test_retry_debits_once(server):
    url=venue(server,2); key=str(uuid4())
    assert order(url,2,key).json() == order(url,2,key).json() == {"id":key,"remaining":0}
    assert order(url,1,key).status_code==409

def test_cancel_is_idempotent(server):
    url=venue(server,3); key=order(url,2).json()["id"]
    for _ in range(2):
        assert httpx.delete(url+"/tickets/"+key).json()=={"remaining":3}
    assert order(url,2,key).status_code==409

def test_last_seat(server):
    url=venue(server,1)
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda _:order(url),range(2)))
    assert sorted(r.status_code for r in responses)==[200,409]
    assert httpx.get(url).json()=={"remaining":0}

def test_invalid_qty(server):
    url=venue(server,4)
    assert order(url,0).status_code==422
    assert httpx.get(url).json()=={"remaining":4}
