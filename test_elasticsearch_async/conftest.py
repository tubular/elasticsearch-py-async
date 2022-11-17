import asyncio
import json
import logging

from pytest import fixture

import aiohttp.web
from elasticsearch_async import AIOHttpConnection, AsyncElasticsearch


@fixture
def connection(event_loop, server, port):
    connection = AIOHttpConnection(port=port, loop=event_loop)
    yield connection
    event_loop.run_until_complete(connection.close())


class DummyElasticsearch(aiohttp.web.Server):

    def __init__(self, **kwargs):
        super().__init__(handler=self.handler, **kwargs)
        self._responses = {}
        self.calls = []

    def register_response(self, path, response={}, status=200):
        self._responses[path] = status, response

    async def handler(self, request):
        url = request.url

        params = dict(request.query)
        body = await request.read()
        body = json.loads(body.decode('utf-8')) if body else ''

        self.calls.append((request.method, url.path, body, params))

        if url.path in self._responses:
            status, body = self._responses.pop(url.path)
            if asyncio.iscoroutine(body):
                body = await body
        else:
            status = 200
            body = {
                'method': request.method,
                'params': params,
                'path': url.path,
                'body': body
            }

        out = json.dumps(body)

        return aiohttp.web.Response(body=out, status=status, content_type='application/json')


i = 0
@fixture
def port():
    global i
    i += 1
    return 8080 + i

@fixture
async def server(event_loop, port):
    server = DummyElasticsearch(debug=True, loop=event_loop)
    f = event_loop.create_server(server, '127.0.0.1', port)
    event_loop.run_until_complete(f)
    yield server
    event_loop.run_until_complete(server.shutdown(timeout=.5))

@fixture
def client(event_loop, server, port):
    logger = logging.getLogger('elasticsearch')
    logger.setLevel(logging.DEBUG)
    c = AsyncElasticsearch([{'host': '127.0.0.1','port': port}], loop=event_loop)
    yield c
    event_loop.run_until_complete(c.transport.close())

@fixture
def sniff_data():
    return {
        "ok" : True,
        "cluster_name" : "super_cluster",
        "nodes" : {
            "node1" : {
                "name": "Thunderbird",
                "transport_address": "node1/127.0.0.1:9300",
                "host": "node1",
                "ip": "127.0.0.1",
                "version": "2.1.0",
                "build": "72cd1f1",
                "http" : {
                    "bound_address" : [ "[fe80::1]:9200", "[::1]:9200", "127.0.0.1:9200" ],
                    "publish_address" : "node1:9200",
                    "max_content_length_in_bytes" : 104857600
                },
                "attributes": {
                    "testattr": "test"
                }
            }
        }
    }
