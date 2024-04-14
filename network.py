from threading import Thread, Lock
import queue
import socket
import time
import zmq
import struct
import pickle

import bpy
from .server import LaunchServer, StopServer

# Constants
PING_INTERVAL = 10
PORT_SERVER_RECV = 42522
PORT_SERVER_SEND = 42533

# Globals
context = None


class Client:
    """Client class manages the connection to the server and provides functions to send OSC data"""
    
    # Connection
    socket = None
    connected = False
    is_host = False
    
    def connect(address='127.0.0.1', port_pub=PORT_SERVER_RECV, port_sub=PORT_SERVER_SEND, launch_server=False) -> bool:
        """Establesh a connection to the sync server"""
        global context
        
        # First close any remaining connections
        Client.disconnect()
        
        # Launch service if on localhost and port is available
        if address == '127.0.0.1' and isPortAvailable(port_pub):
            if launch_server:
                ProxyServer.launch(port_pub, port_sub)
                Client.is_host = True
            else:
                print(f"Error: Local server is not running")
                return False
            
        # Launch receiver
        Client.connected = True
        Receiver.launch(address, port_sub)
        
        # Connect to server
        Client.socket = context.socket(zmq.PUB)
        Client.socket.connect(f"tcp://{address}:{port_pub}")
                
        # Ping timer (?)
        #bpy.app.timers.register(Client.ping, first_interval=PING_INTERVAL)
        return True

    def launchServer(port_pub, port_sub) -> bool:
        return True


    def disconnect():
        # Only close with an active connection
        if Client.connected:
            # Unregister ping function
            #if bpy.app.timers.is_registered(Client.ping):
            #    bpy.app.timers.unregister(Client.ping)

            Client.connected = False
            Client.is_host = False
            Client.socket.close()
            # Wait for receiver to finish
            Receiver.join()
    

    def sendOsc(data_path: str, obj):
        if Client.connected:
            # Send message
            try:
                Client.socket.send_multipart([data_path.encode('utf-8'), pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)])
                
            except Exception as err:
                print(f"Error: Sync communication {str(err)}")
    


class Receiver:
    """Receiver thread to receive and process sync commands of other instances"""
    thread = None
    sync_props = {}
    queue = queue.Queue()
    
    def registerSync(obj: bpy.types.Object, prop: str, address: str) -> int:
        Receiver.sync_props[(obj, prop)] = address

    def unregisterSync(obj: bpy.types.Object, prop: str):
        try:
            del Receiver.sync_props[(obj, prop)]
        except:
            pass
        
    def launch(address, port_sub):
        Receiver.thread = Thread(target=Receiver.run, args=(address, port_sub))
        Receiver.thread.start()

        
    def join():
        if Receiver.thread is not None:
            Receiver.thread.join()


    def run(address, port_sub):
        global context

        # Setup sockets
        osc_sock = context.socket(zmq.SUB)
        osc_sock.connect(f"tcp://{address}:{port_sub}")
        # Filter TODO
        osc_sock.setsockopt(zmq.SUBSCRIBE, b'/')

        # Poller
        poller = zmq.Poller()
        poller.register(osc_sock, zmq.POLLIN)
        
        while Client.connected:
            # Poll loop
            if poller.poll(100):
                # Data received
                
                if True:#(poller.pollin(0)): # OSC Message TODO pollin does not exist
                    # Parse message
                    try:
                        data = osc_sock.recv_multipart()
                        osc_msg, osc_data = data[0], pickle.loads(data[1])
                        
                        # Store in queue
                        Receiver.queue.put_nowait((osc_msg, osc_data))
                        
                        # Register timer
                        if not bpy.app.timers.is_registered(Receiver.updateOnMainthread):
                            bpy.app.timers.register(Receiver.updateOnMainthread)
                        
                    except Exception as e:
                        print(f"Error: Can't read received data ({str(e)})")
    
        # Clean up connection
        osc_sock.close()


    def updateOnMainthread():
        """Blender data must be updated from the main thread. A timer function is called from the main thread, thus updates can happen here"""
        while not Receiver.queue.empty():
            osc_msg, osc_data = Receiver.queue.get()
            # Path from other instances is /<scene>/<obj>/channel
            
            # Check if there is an object with this name
            osc_msg = osc_msg.decode("utf-8")
            obj_name, prop_name = osc_msg.rsplit('/', 1)
            if obj_name != "" and not obj_name in bpy.data.objects:
                # Create empty
                empty = bpy.data.objects.new(obj_name, None)
                empty.use_fake_user = True
            
            # Update hidden empties
            try:
                obj = bpy.data.objects[obj_name]
                # Find and update channel
                match prop_name:
                    case 'location':
                        obj.location = osc_data
                    case 'rotation':
                        obj.rotation_euler = osc_data
                    case 'scale':
                        obj.scale = osc_data
                    case _:
                        obj[prop_name] = osc_data
            except Exception as e:
                print(f"Error: Can't set property '{prop_name}': {str(e)}")
            
            # Dispatch
            del_list = []
            for obj_prop, obj_addr in Receiver.sync_props.items():
                if obj_addr == osc_msg:
                    try:
                        obj, prop = obj_prop
                        setattr(obj, prop, osc_data)
                    except Exception as e:
                        del_list.append(obj_prop)
            # Delete invalid objects
            for obj in del_list:
                del Receiver.sync_props[obj]

            
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
        sub_sock = context.socket(zmq.SUB)
        sub_sock.setsockopt(zmq.SUBSCRIBE, b'')
        pub_sock = context.socket(zmq.PUB)
        sub_sock.bind(f"tcp://*:{port_xsub}")
        pub_sock.bind(f"tcp://*:{port_xpub}")

        # Poller
        poller = zmq.Poller()
        poller.register(sub_sock, zmq.POLLIN)
        while ProxyServer.running:
            # Poll loop
            if poller.poll(100):
                pub_sock.send_multipart(sub_sock.recv_multipart())



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


