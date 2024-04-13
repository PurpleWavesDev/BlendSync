from threading import Thread, Lock
import queue
import socket
import zmq
import time

import bpy
from .server import LaunchServer, StopServer

# Constants
PING_INTERVAL = 10
PORT_SERVER_RECV = 5012
PORT_SERVER_SEND = 5013

# Globals
context = None


class Client:
    """Client class manages the connection to the server and provides functions to send OSC data"""
    
    # Connection
    socket = None
    connected = False
    is_host = False
    
    def connect(address='127.0.0.1', port_pub=PORT_SERVER_RECV, port_sub=PORT_SERVER_SEND) -> bool:
        """Establesh a connection to the sync server"""
        global context
        
        # First close any remaining connections
        Client.disconnect()
        
        # Launch service if on localhost and port is available
        if address == '127.0.0.1' and isPortAvailable(port_pub):
            ProxyServer.launch(port_pub, port_sub)
            Client.is_host = True
            # Wait for server to start up TODO not needed when host doesn't connect to proxy itself
            time.sleep(0.5)

        #else:
        # Connect to server
        Client.socket = context.socket(zmq.PUB)
        Client.socket.connect(f"tcp://{address}:{port_pub}")
        
        # Try to init connectionSend an init message and wait for answer
        if Client.init():
            # Launch receiver
            Receiver.launch(address, port_sub)
            # Launch ping timer
            bpy.app.timers.register(Client.ping, first_interval=PING_INTERVAL)
            return True
            
        print(f"Error: Can't connect to server {address}:{port_pub}")
        return False


    def disconnect():
        # Unregister ping function
        if bpy.app.timers.is_registered(Client.ping):
            bpy.app.timers.unregister(Client.ping)

        # Only close with an active connection
        if Client.connected:
            Client.connected = False
            Client.socket.close()
            # Wait for receiver to finish
            Receiver.join()
    
    def init():
        Client.socket.send(b"Init")
        Client.connected = True
        return Client.connected

    def sync(data_path, dtype, value, reconnect=True, force=False):
        if not Client.connected and reconnect:
            # Try to connect
            bpy.ops.blendsync.connect()
            
        if Client.connected or force:
            # Send message
            try:
                ipc.send(Client.socket, message) # TODO
            except Exception as err:
                print(f"Error: Sync communication {str(err)}")
                Client.disconnect()
    
    def ping():
        """Ping timer gets reset every time a message is received. Function is called when timeout is exceeded"""
        if Client.connected:
            print("Error: Ping timeout")
            #Client.disconnect()
        
        # Stop timer
        return None


class Receiver:
    """Receiver thread to receive and process sync commands of other instances"""
    thread = None
    lock = Lock()
    queue = queue.Queue()
    
    def registerSync(obj: bpy.types.Object, address: str) -> int:
        #serviceRemoveReq(image_name)
        id, _  = serviceGetReq(image_name)
        
        # Add new ID
        if id is None:
            id = request_count
            request_count += 1
        
        image_requests[id] = (image_name, False)
        return id

    def unregisterSync(obj: bpy.types.Object):
        global image_requests
        global request_count
        
        # Delete old entry
        old_ids = [id for id, data in image_requests.items() if data[0] == image_name]
        for id in old_ids:
            del image_requests[id]
        
    def launch(address, port_sub):
        Receiver.thread = Thread(target=Receiver.run, args=(address, port_sub))
        Receiver.thread.start()

        
    def join():
        if Receiver.thread is not None:
            Receiver.thread.join()


    def run(address, port_sub):
        global context

        # Setup socket
        recv_sock = context.socket(zmq.SUB)
        recv_sock.connect(f"tcp://{address}:{port_sub}")
        # Set timeout and disconnect after timeout option TODO
        recv_sock.setsockopt(zmq.LINGER, 0)
        # Filter TODO
        #topicfilter = "10001"
        #recv_sock.setsockopt(zmq.SUBSCRIBE, topicfilter)

        # Poller
        poller = zmq.Poller()
        poller.register(recv_sock, zmq.POLLIN)
        
        while Client.connected:
            # Poll loop
            if poller.poll(100):
                # Data received
                osc_msg = recv_sock.recv()
                print("Sub: " + osc_msg)

                #try:
                #    id, img_data = receive_array(recv_sock)
                #    with Receiver.lock:
                #        pass
                #    
                #except Exception as e:
                #    print(f"Error: Can't read received data ({str(e)})")
    
        # Clean up connection
        recv_sock.close()


    def updateOnMainthread():
        """Blender data must be updated from the main thread. A timer function is called from the main thread, thus updates can happen here"""
        while not Receiver.queue.empty():
            with Receiver.lock:
                path, data = Receiver.queue.get()
            
            # Update hidden empties
            # Check if there is an object
            if path in bpy.data.objects:
                # Update image
                bpy.data.images[image_requests[id][0]].pixels.foreach_set(pix_data)
                # Set update flag and mark as received
                bpy.data.images[image_requests[id][0]].update_tag()
                image_requests[id] = (image_requests[id][0], True)
            else:
                # Create empty
                pass
            
            # Update objects
            
        return None


class ProxyServer:
    """Stateless proxy that receives published messages and forwards them to all subscribers"""
    thread = None
    running = False
    
    def launch(port_xsub, port_xpub):
        ProxyServer.thread = Thread(target=ProxyServer.run, args=(port_xsub, port_xpub))
        ProxyServer.thread.start()
        
    def stop():
        if ProxyServer.thread is not None:
            ProxyServer.running = False
            ProxyServer.thread.join()

    
    def run(port_xsub, port_xpub):
        global context
        
        ProxyServer.running = True
        sub_sock = context.socket(zmq.XSUB)
        pub_sock = context.socket(zmq.XPUB)
        sub_sock.bind(f"tcp://*:{port_xsub}")
        pub_sock.bind(f"tcp://*:{port_xpub}")

        # Poller
        poller = zmq.Poller()
        poller.register(sub_sock, zmq.POLLIN)
        
        while ProxyServer.running:
            # Poll loop
            if poller.poll(500):
                osc_msg = sub_sock.recv()
                print("Proxy: " + osc_msg)
                if osc_msg is not None:
                    pub_sock.send(osc_msg)



# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------        
def getHostname() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    return s.getsockname()[0]

def isPortAvailable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0



def register():
    global context
    context = zmq.Context()


def unregister():
    global context
    
    # Disconnect and stop threads
    Client.disconnect()
    
    # Stop server thread
    ProxyServer.stop()
    
    if context is not None:
        context.destroy()


