import bpy
from bpy.types import Scene, Object, WindowManager, PropertyGroup
from bpy.props import *

from .network import Client, PORT_SERVER_RECV, PORT_SERVER_SEND
from .sync import SendUpdate, ReceiveUpdate

## Poll functions

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
    poll: BoolProperty(default=False, name="Path Poll")


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
   
