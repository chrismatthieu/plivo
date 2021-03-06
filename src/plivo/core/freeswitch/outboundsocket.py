# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Outbound Event Socket class

This manage Event Socket communication with the Freeswitch Server
"""

from gevent.server import StreamServer
from gevent.timeout import Timeout
from plivo.core.freeswitch.eventsocket import EventSocket
from plivo.core.freeswitch.transport import OutboundTransport
from plivo.core.errors import ConnectError



class OutboundEventSocket(EventSocket):
    '''
    FreeSWITCH Outbound Event Socket.

    A new instance of this class is created for every call/ session from FreeSWITCH.
    '''
    def __init__(self, socket, address, filter="ALL", pool_size=500, connect_timeout=5):
        EventSocket.__init__(self, filter, pool_size)
        self.transport = OutboundTransport(socket, address, connect_timeout)
        self._uuid = None
        self._channel = None
        # Connects.
        self.connect()
        # Runs the main function .
        try:
            self.run()
        finally:
            self.disconnect()

    def connect(self):
        super(OutboundEventSocket, self).connect()
        # Starts event handler for this client/session.
        self.start_event_handler()

        # Sends connect and sets timeout while connecting.
        timer = Timeout(self.transport.get_connect_timeout())
        timer.start()
        try:
            connect_response = self._protocol_send("connect")
            if not connect_response.is_success():
                self.disconnect()
                raise ConnectError("Error while connecting")
        except Timeout:
            self.disconnect()
            raise ConnectError("Timeout connecting")
        finally:
            timer.cancel()

        # Sets channel and channel unique id from this event
        self._channel = connect_response
        self._uuid = connect_response.get_header("Unique-ID")

        # Set connected flag to True
        self.connected = True

        # Sets event filter or raises ConnectError
        if self._filter:
            filter_response = self.eventplain(self._filter)
            if not filter_response.is_success():
                self.disconnect()
                raise ConnectError("Event filter failure")

    def get_channel(self):
        return self._channel

    def get_channel_unique_id(self):
        return self._uuid

    def run(self):
        '''
        This method must be implemented by subclass.

        This is the entry point for outbound application.
        '''
        pass


class OutboundServer(StreamServer):
    '''
    FreeSWITCH Outbound Event Server
    '''
    def __init__(self, address, handle_class, filter="ALL"):
        self._filter = filter
        #Define the Class that will handle process when receiving message
        self._handle_class = handle_class
        StreamServer.__init__(self, address, self.do_handle)

    def do_handle(self, socket, address):
        self._handle_class(socket, address, self._filter)




if __name__ == '__main__':
    outboundserver = OutboundServer(('127.0.0.1', 8084), OutboundEventSocket)
    outboundserver.serve_forever()
