from threading import Thread, Lock
import queue
import socket
import time
import zmq
import struct
import pickle
from oscpy.server import OSCThreadServer

import bpy


# Constants
PING_INTERVAL = 10
PORT_SERVER_RECV = 8000
PORT_SERVER_SEND = 7000

# Globals
context = None


class Client:
    """Client class manages the connection to the server and provides functions to send OSC data"""
    
    # Connection
    socket = None
    connected = False
    is_host = False
    address=""
    port_pub=0
    port_sub=0
    
    def connect(address='127.0.0.1', port_pub=PORT_SERVER_RECV, port_sub=PORT_SERVER_SEND, launch_server=False) -> bool:
        """Establesh a connection to the sync server"""
        global context
        
        # First close any remaining connections
        Client.disconnect()
        
        # Launch service if on localhost and port is available
        if address == '127.0.0.1' and isPortAvailable(port_pub):
            if launch_server:
                Client.launchServer(port_pub, port_sub)
            else:
                print(f"Error: Local server is not running")
                return False
            
        Client.connected = True
        Client.address = address
        Client.port_pub = port_pub
        Client.port_sub = port_sub
        # Launch receiver
        Receiver.launch(address, port_sub, Client.is_host)
        
        # Connect to server
        Client.socket = context.socket(zmq.PUB)
        Client.socket.connect(f"tcp://{address}:{port_pub}")
        
        # Ping timer (?)
        #bpy.app.timers.register(Client.ping, first_interval=PING_INTERVAL)
        return True

    def launchServer(port_xsub, port_xpub) -> bool:
        ProxyServer.launch(port_xsub, port_xpub)
        Client.is_host = True
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
    
    def publishPath(data_path):
        if Client.connected:
            # Send message
            try:
                Client.socket.send_multipart([b'>PUB', pickle.dumps(data_path)])
            except Exception as err:
                print(f"Error: Sync communication {str(err)}")


class Receiver:
    """Receiver thread to receive and process sync commands of other instances"""
    thread = None
    osc_server = None
    sync_props = {}
    poll_objects = {}
    queue = queue.Queue()
    register_lock = Lock()
    
    def registerSync(obj: bpy.types.Object, prop: str, address: str) -> int:
        Receiver.sync_props[(obj, prop)] = address

    def unregisterSync(obj: bpy.types.Object, prop: str):
        try:
            del Receiver.sync_props[(obj, prop)]
        except:
            pass
        
    def registerPoll(obj, recv_only):
        Receiver.poll_objects[obj] = recv_only
    
    def unregisterPoll(obj):
        try:
            del Receiver.poll_objects[obj]
        except:
            pass            
        
    def launch(address, port_sub, is_host=False):
        Receiver.thread = Thread(target=Receiver.run, args=(address, port_sub))
        Receiver.thread.start()
        
        ## Additional OSC server TODO: Own protocol should be OSC compatible instead of having extra server running
        if is_host:
            Receiver.osc_server = OSCThreadServer(default_handler=Receiver.oscHandler)
            Receiver.osc_server.listen(address="0.0.0.0", port=port_sub+1, default=True)

        
    def join():
        if Receiver.osc_server is not None:
            Receiver.osc_server.stop()
            
        if Receiver.thread is not None:
            Receiver.thread.join()

    def oscHandler(address, *values):
        address = address.decode('utf8')
        data = [v.decode('utf8') if isinstance(v, bytes) else v\
            for v in values if values]
        data = data[0] if len(data) == 1 else data
        
        # Store in queue
        Receiver.queue.put_nowait((address, data))
                                
        # Register timer
        with Receiver.register_lock:
            if not bpy.app.timers.is_registered(Receiver.updateOnMainthread):
                bpy.app.timers.register(Receiver.updateOnMainthread)



    def run(address, port_sub):
        global context

        # Setup sockets
        osc_sock = context.socket(zmq.SUB)
        osc_sock.connect(f"tcp://{address}:{port_sub}")
        # Filter TODO
        osc_sock.setsockopt(zmq.SUBSCRIBE, b'/') # OSC Strings
        osc_sock.setsockopt(zmq.SUBSCRIBE, b'>') # Commands

        # Poller
        poller = zmq.Poller()
        poller.register(osc_sock, zmq.POLLIN)
        
        while Client.connected:
            # Poll loop
            if poller.poll(100):
                # Data received
                try:
                    if True:#(poller.pollin(0)): # OSC Message TODO pollin does not exist
                        # Parse message
                        data = osc_sock.recv_multipart()
                        osc_msg, osc_data = data[0].decode("utf-8"), pickle.loads(data[1])
                        
                        # Store in queue 
                        Receiver.queue.put_nowait((osc_msg, osc_data))
                        
                        # Register timer
                        with Receiver.register_lock:
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
                        
            if osc_msg[0] == '/':
                ## OSC Message
                # Check for special cases
                if len(osc_msg) == 1:
                    osc_msg = "/default/default"
                obj_name, prop_name = osc_msg.rsplit('/', 1)
                if obj_name == "": obj_name = "/default"
                if prop_name == "": prop_name = "default"
                # Create empty
                Receiver.createOscEmpty(obj_name)
                
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
                    obj.update_tag()
                    bpy.types.Scene.update_render_engine()
                    bpy.context.view_layer.update()
                    #bpy.types.Scene.update() # No update or update_tag exists, anything else?
                    
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
                    
            else:
                ## Command Message
                match osc_msg:
                    case '>PUB':
                        # Pub message, assign to all pollers
                        try:
                            for obj, recv_only in Receiver.poll_objects.items():
                                obj.blendsync.recv_path = osc_data
                                if not recv_only:
                                    obj.blendsync.send_path = osc_data
                                obj.blendsync.poll = False
                        except Exception as e:
                            print(f"Error: Can't assign published path '{osc_data}'")
                        finally:
                            Receiver.poll_objects.clear()
                        
                        # Also create empty if it doesn't exist yet
                        Receiver.createOscEmpty(osc_data)
            
        return None

    def createOscEmpty(obj_name):
        if obj_name != "" and not obj_name in bpy.data.objects:
            empty = bpy.data.objects.new(obj_name, None)
            empty.is_osc_proxy = True
            empty.use_fake_user = True


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
    try:
        # "static" variable to avoid recalling connect every time
        return getHostname.host_name
    except:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
        getHostname.host_name = s.getsockname()[0]
        return getHostname.host_name

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


