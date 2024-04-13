import bpy
from bpy.types import Scene, Object, WindowManager, PropertyGroup
from bpy.props import *

from .client import Client


## Poll functions
def IsSyncActive(self, obj):
    return True #obj.

## Property classes
class BlendSync_Props(PropertyGroup):
    connected: BoolProperty(get=lambda self: Client.connected)
    # Settings
    server_addr: StringProperty(default="localhost", name="Server")
    server_port: IntProperty(default=4250, name="Port")
    
class BlendSync_Object(PropertyGroup):
    pass


classes = (
    BlendSync_Props,
    BlendSync_Object,
)

## (Un-)Register
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    # Register custom objects (defined thorugh pollers)
    #Scene.blendsync_active = bpy.props.PointerProperty(
    #    type=bpy.types.Object,
    #    poll=IsSyncActive
    #)

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
   
