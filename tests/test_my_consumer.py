import pytest
from channels.testing import WebsocketCommunicator

from tests.asgi import application


@pytest.mark.asyncio
async def test_my_consumer():

    communicator = WebsocketCommunicator(application, "/my-consumer/")
    connected, subprotocol = await communicator.connect()
    assert connected

    await communicator.send_to("ping-a-message")
    pong = await communicator.receive_from()  # noqa: F841
    assert pong == "ping-a-message"

    await communicator.disconnect()
