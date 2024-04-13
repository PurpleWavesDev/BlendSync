import math
import mathutils
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from . import properties as props
from .client import *


# -------------------------------------------------------------------
#   Global data
# -------------------------------------------------------------------

# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

class BLENDSYNC_OT_connect(Operator):
    """Connects to the blendsync server"""
    bl_label = "Connect"
    bl_idname = "blendsync.connect"
    bl_description = "(Re-)Connects to the blendsync server"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        Client.connect() # TODO Properties
        
        # Return finished if connected successfully 
        if wm_syncprops.connected:
            return{'FINISHED'}

        self.report({"WARNING"}, f"Can't establish a connection to server {wm_syncprops.server_addr}:{wm_syncprops.server_port}")
        return{'CANCELLED'}



# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def depthgraphUpdated(scene):
    pass
    

def timerCallback():
    
    return 1.0


# -------------------------------------------------------------------
#   Scene API and Helpers
# -------------------------------------------------------------------


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    BLENDSYNC_OT_connect,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Event handlers
    #bpy.app.handlers.frame_change_pre.append(frameChange)
    bpy.app.handlers.depsgraph_update_post.append(depthgraphUpdated)
    bpy.app.timers.register(timerCallback)


def unregister():
    if bpy.app.timers.is_registered(timerCallback):
        bpy.app.timers.unregister(timerCallback)
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

