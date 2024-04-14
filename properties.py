import bpy
from bpy.types import Scene, Object, WindowManager, PropertyGroup
from bpy.props import *

from .network import Client, Receiver, PORT_SERVER_RECV, PORT_SERVER_SEND
from .sync import enableSync, disableSync

## Poll functions

## Update callbacks
def SendUpdate(self, context):
    obj = context.object
    if self.send_enabled:
        # Check connection
        if not Client.connected:
            Client.connect(launch_server=True) # TODO Default ports or from props?
        # Register object props
        enableSync(obj.blendsync.send_path+'/location', obj, 'location')
        enableSync(obj.blendsync.send_path+'/rotation', obj, 'rotation_euler')
        enableSync(obj.blendsync.send_path+'/scale', obj, 'scale')
    else:
        disableSync(obj.blendsync.send_path+'/location')
        disableSync(obj.blendsync.send_path+'/rotation')
        disableSync(obj.blendsync.send_path+'/scale')
        
        

def ReceiveUpdate(self, context):
    obj = context.object
    if self.recv_enabled:
        # Check connection
        if not Client.connected:
            Client.connect(launch_server=True)
        # Register object props
        Receiver.registerSync(obj, 'location', obj.blendsync.recv_path+'/location')
        Receiver.registerSync(obj, 'rotation_euler', obj.blendsync.recv_path+'/rotation')
        Receiver.registerSync(obj, 'scale', obj.blendsync.recv_path+'/scale')
    else:
        Receiver.unregisterSync(obj, 'location')
        Receiver.unregisterSync(obj, 'rotation_euler')
        Receiver.unregisterSync(obj, 'scale')



## Property classes
class BlendSync_Props(PropertyGroup):
    connected: BoolProperty(get=lambda self: Client.connected)
    # Settings
    server_addr: StringProperty(default="127.0.0.1", name="Server")
    server_port_cli2srv: IntProperty(default=PORT_SERVER_RECV, name="Client to Server Port")
    server_port_srv2cli: IntProperty(default=PORT_SERVER_SEND, name="Server to Client Port")
    
class BlendSync_Object(PropertyGroup):
    send_enabled: BoolProperty(default=False, name="Send", update=SendUpdate)
    recv_enabled: BoolProperty(default=False, name="Receive", update=ReceiveUpdate)
    
    send_path: StringProperty(default="", name="OSC Path")
    recv_path: StringProperty(default="", name="OSC Path")


classes = (
    BlendSync_Props,
    BlendSync_Object,
)

## (Un-)Register
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Assign properties
    WindowManager.blendsync = PointerProperty(type=BlendSync_Props, name="BlendSync Properties")
    Object.blendsync = PointerProperty(type=BlendSync_Object, name="BlendSync Object")
   

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    del Object.blendsync
    del WindowManager.blendsync
   
