import bpy
from bpy.types import Scene, Object, WindowManager, PropertyGroup
from bpy.props import *

from .network import Client, PORT_SERVER_RECV, PORT_SERVER_SEND
from .sync import SendUpdate, ReceiveUpdate, UpdateSendPath, UpdateRecvPath

def getOscPaths(self, context, edit_text) -> list:
    name = bpy.path.basename(bpy.context.blend_data.filepath)
    if name == "": name = "unnamed"
    elif '.' in name: name = name.split('.')[0]
    return [f"/blend/{name}/{context.object.name}"] + [obj.name for obj in bpy.data.objects if obj.is_osc_proxy]


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
    
    send_path: StringProperty(name="OSC Send Path", default="/blend", update=UpdateSendPath, search=getOscPaths)
    recv_path: StringProperty(name="OSC Receive Path", default="/blend", update=UpdateRecvPath, search=getOscPaths)
    poll: BoolProperty(default=False, name="Path Poll")


## Preferences
#class Preferences(AddonPreferences):
#    example: StringProperty(
#        name="foo"
#        update=callbackfunc
#    )


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
    Object.is_osc_proxy = BoolProperty(default=False, name="Is OSC channel proxy", options=set())

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    # Delete properties
    del Object.is_osc_proxy
    del Object.blendsync
    del WindowManager.blendsync
   
