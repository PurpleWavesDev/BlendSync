import math
import mathutils
import numpy as np
import bpy
from bpy.props import *
from bpy.types import Operator, Panel, PropertyGroup, UIList

from . import properties as props
from .network import *


# -------------------------------------------------------------------
#   Global data
# -------------------------------------------------------------------
sync_paths = {}

# -------------------------------------------------------------------
#   Operators
# -------------------------------------------------------------------

class BLENDSYNC_OT_connect(Operator):
    """Connects to the blendsync server"""
    bl_label = "Connect"
    bl_idname = "blendsync.connect"
    bl_description = "(Re-)Connects to the blendsync server"
    bl_options = {'REGISTER', 'UNDO'}
    
    launch_server = BoolProperty(default=False, name="Launch Server")
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        Client.connect(wm_syncprops.server_addr, wm_syncprops.server_port_cli2srv, wm_syncprops.server_port_srv2cli, self.launch_server)
        
        # Return finished if connected successfully 
        if wm_syncprops.connected:
            return{'FINISHED'}

        self.report({"WARNING"}, f"Can't establish a connection to server {wm_syncprops.server_addr}:{wm_syncprops.server_port_cli2srv}")
        return{'CANCELLED'}
    
class BLENDSYNC_OT_launch(Operator):
    """Launches the Blendsync Server, instance becomes host"""
    bl_label = "Launch Server"
    bl_idname = "blendsync.launch"
    bl_description = "Launches the Blendsync Server, instance becomes host"
    bl_options = {'REGISTER'}
    
    launch_server = BoolProperty(default=False, name="Launch Server")
    
    @classmethod
    def poll(cls, context):
        return not context.window_manager.blendsync.connected

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        Client.launchServer(wm_syncprops.server_port_cli2srv, wm_syncprops.server_port_srv2cli) # TODO
        
        # Return finished if connected successfully 
        if wm_syncprops.connected:
            return{'FINISHED'}

        self.report({"WARNING"}, f"Unable to launch server on ports {wm_syncprops.server_port_cli2srv} and {wm_syncprops.server_port_srv2cli}")
        return{'CANCELLED'}


class BLENDSYNC_OT_publish(Operator):
    """Publishes a channel or object to all other instances"""
    bl_label = "Publish"
    bl_idname = "blendsync.publish"
    bl_description = "Publishes an channel to all other instances"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return context.object.blendsync.send_enabled

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        # Connect first if no connection has been established
        if wm_syncprops.connected:
            
            
            return{'FINISHED'}

        self.report({"WARNING"}, f"No connection established")
        return{'CANCELLED'}
    
class BLENDSYNC_OT_subscribe(Operator):
    """Subscribes to an object or channel of another instance as soon as will be published"""
    bl_label = "Subscribe"
    bl_idname = "blendsync.subscribe"
    bl_description = "Subscribes to an object or channel of another instance as soon as will be published"
    bl_options = {'REGISTER', 'UNDO'}
        
    @classmethod
    def poll(cls, context):
        return context.object.blendsync.recv_enabled

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        # Connect first if no connection has been established
        if wm_syncprops.connected:
            
            
            return{'FINISHED'}

        self.report({"WARNING"}, f"No connection established")
        return{'CANCELLED'}



# -------------------------------------------------------------------
#   Event handlers
# -------------------------------------------------------------------
def depthgraphUpdated(scene):
    global sync_paths
    del_list = []
    for path, data in sync_paths.items():
        obj, prop, last_val = data
        try:
            val = getattr(obj, prop)
            # Cast to list if necessary
            match type(val):
                case mathutils.Vector|mathutils.Euler|mathutils.Matrix:
                    val = list(val)
            if last_val != val:
                Client.sendOsc(path, val)
                sync_paths[path] = (obj, prop, val)
        except Exception as e:
            # Object or attribute invalid
            del_list.append(path)
    
    # Delete invalid paths
    for path in del_list:
        del sync_paths[path]


# -------------------------------------------------------------------
#   Sync API
# -------------------------------------------------------------------
def enableSync(path, obj, prop):
    global sync_paths
    sync_paths[path] = (obj, prop, None)

def disableSync(path):
    global sync_paths
    if path in sync_paths:
        del sync_paths[path]

def updateSync(old_path, new_path):
    global sync_paths
    if old_path in sync_paths and not new_path in sync_paths:
        sync_paths[new_path] = sync_paths[old_path]
        del sync_paths[old_path]
        return True
    return False

# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    BLENDSYNC_OT_connect,
    BLENDSYNC_OT_publish,
    BLENDSYNC_OT_subscribe,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Event handlers
    #bpy.app.handlers.frame_change_pre.append(frameChange)
    bpy.app.handlers.depsgraph_update_post.append(depthgraphUpdated)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

