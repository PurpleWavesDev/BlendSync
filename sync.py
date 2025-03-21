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
    bl_options = {'REGISTER'}
    
    launch_server: BoolProperty(default=True, name="Launch Server")
    
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

## TODO: Actually not needed, connect OP can also launch server
#class BLENDSYNC_OT_launch(Operator):
#    """Launches the blendsync server, instance becomes host"""
#    bl_label = "Launch Server"
#    bl_idname = "blendsync.launch"
#    bl_description = "Launches the blendsync server, instance becomes host"
#    bl_options = {'REGISTER'}
#        
#    @classmethod
#    def poll(cls, context):
#        return not Client.connected
#
#    def execute(self, context):
#        wm_syncprops = context.window_manager.blendsync
#        
#        # Return finished if start is successful
#        if Client.launchServer(wm_syncprops.server_port_cli2srv, wm_syncprops.server_port_srv2cli):
#            return{'FINISHED'}
#
#        self.report({"WARNING"}, f"Can't launch server on ports {wm_syncprops.server_port_cli2srv} and {wm_syncprops.server_port_srv2cli}")
#        return{'CANCELLED'}


class BLENDSYNC_OT_clearProxies(Operator):
    """Removes all OSC proxy objects"""
    bl_label = "Clear Proxy Objects"
    bl_idname = "blendsync.clear_proxies"
    bl_description = "Removes all OSC proxy objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.is_osc_proxy:
                obj.use_fake_user = False
                bpy.data.objects.remove(obj)
                
        return{'FINISHED'}


class OBJECT_OT_blendsyncPublish(Operator):
    """Publishes a channel or object to all other instances"""
    bl_label = "Publish"
    bl_idname = "object.blendsync_publish"
    bl_description = "Publishes an channel to all other instances"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.object
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        # Check connection
        if not Client.connected:
            Client.connect(launch_server=True) # TODO Default ports or from props?
        
        # Only works when a connection is established
        if wm_syncprops.connected:
            Client.publishPath(obj.blendsync.send_path)
            return{'FINISHED'}

        self.report({"WARNING"}, f"No connection established")
        return{'CANCELLED'}


class OBJECT_OT_blendsyncPoll(Operator):
    """Polls the object or channel from another instance when it is published"""
    bl_label = "Poll"
    bl_idname = "object.blendsync_poll"
    bl_description = "Polls the object or channel from another instance when it is published"
    bl_options = {'REGISTER', 'UNDO'}
    
    recv_only: BoolProperty(default=False, name="Poll for receive channel only")
        
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        obj = context.object
        scn = context.scene
        
        # Check connection
        if not Client.connected:
            Client.connect(launch_server=True) # TODO Default ports or from props?
        
        if not obj.blendsync.poll:
            # Add to poll list
            Receiver.registerPoll(obj, self.recv_only)
            obj.blendsync.poll = True
        else:
            Receiver.unregisterPoll(obj)
            obj.blendsync.poll = False
            
        return{'FINISHED'}



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


## Send/Receive Property Update callbacks
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

def UpdateSendPath(self, context):
    if len(self.send_path) == 0 or self.send_path[0] != '/':
        self['send_path'] = '/'+self.send_path

def UpdateRecvPath(self, context):
    if len(self.recv_path) == 0 or self.recv_path[0] != '/':
        self['recv_path'] = '/'+self.recv_path


# -------------------------------------------------------------------
#   Register & Unregister
# -------------------------------------------------------------------

classes = (
    BLENDSYNC_OT_connect,
    BLENDSYNC_OT_clearProxies,
    OBJECT_OT_blendsyncPublish,
    OBJECT_OT_blendsyncPoll,
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

