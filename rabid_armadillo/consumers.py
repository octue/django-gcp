import logging
from channels.generic.websocket import WebsocketConsumer


logger = logging.getLogger(__name__)


class MyConsumer(WebsocketConsumer):
    """ An example consumer
    """

    def connect(self):
        self.accept()

    def receive(self, text_data=None, bytes_data=None):
        """ Receive text data from websocket and ping it back to everybody connected to the channel
        """

        # Get the incoming message data and pong it straight back to everybody connected.
        # Dumbest consumer ever but hey, writing this bit is your job, not mine!
        self.send(text_data=text_data)

    def disconnect(self, close_code):
        # Called when the socket closes
        pass
