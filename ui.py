import bpy
from bpy.types import Panel, Menu

from .sync import *
from .network import *


# -------------------------------------------------------------------
# 3D View Panel: Status, address, port
# -------------------------------------------------------------------

class VIEW3D_PT_blendsync(Panel):
    """Panel in the 3D view for blendsync configuration"""
    bl_space_type = "VIEW_3D" 
    bl_region_type = "UI" 

    bl_category = "Sync" 
    bl_label = "BlendSync" 
    bl_idname = "VIEW3D_PT_blendsync" 
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        # Connection status
        if wm_syncprops.connected:
            layout.label(text=f"Connected to {Client.address}", icon="PROP_ON")
            layout.label(text=f"Ports: {Client.port_pub} (send), {Client.port_sub} (recv)")
            if Client.is_host: layout.label(text="Instance is hosting server")
        else:
            layout.label(text="Disconnected", icon="PROP_OFF")
        layout.separator()
        
        # Connection OPs
        layout.prop(wm_syncprops, 'server_addr')
        layout.prop(wm_syncprops, 'server_port_cli2srv')
        layout.prop(wm_syncprops, 'server_port_srv2cli')
        row = layout.row(align=True)
        row.operator(BLENDSYNC_OT_connect.bl_idname, icon="URL").launch_server = False
        row.operator(BLENDSYNC_OT_connect.bl_idname, text="Launch server", icon="QUIT").launch_server = True
        layout.separator()
        
        # Data management
        layout.operator(BLENDSYNC_OT_clearProxies.bl_idname, icon="CANCEL")
        

class OBJECT_PT_blendsync(Panel):
    """Panel in the object properties for blendsync"""
    bl_idname = 'OBJECT_PT_blendsync'
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = "BlendSync"
    bl_context = "object"
        
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation
        scn = context.scene
        obj = context.object
        wm_syncprops = context.window_manager.blendsync

        # Subpanels for send and receive
        header, panel = self.layout.panel('blendsync_send', default_closed=False)
        header.use_property_split=False
        header.prop(obj.blendsync, 'send_enabled', text='')
        header.label(text="Send")
        if panel:
            panel.enabled=obj.blendsync.send_enabled
            layout.prop(obj.blendsync, 'send_path')
            split = layout.split(factor=0.4)
            split.label(text='')
            split.operator(OBJECT_OT_blendsyncPublish.bl_idname)
            
        header, panel = self.layout.panel('blendsync_recv', default_closed=False)
        header.use_property_split=False
        header.prop(obj.blendsync, 'recv_enabled', text='')
        header.label(text="Receive")
        if panel:
            panel.enabled=obj.blendsync.recv_enabled
            layout.prop(obj.blendsync, 'recv_path')
            split = layout.split(factor=0.4, align=True)
            split.label(text='')
            if not obj.blendsync.poll:
                split.operator(OBJECT_OT_blendsyncPoll.bl_idname, text="Poll Receive").recv_only=True
                split.operator(OBJECT_OT_blendsyncPoll.bl_idname, text="Poll both").recv_only=False
            else:
                split.operator(OBJECT_OT_blendsyncPoll.bl_idname, text="Polling...")



# -------------------------------------------------------------------
# un/register
# -------------------------------------------------------------------

classes =(
    VIEW3D_PT_blendsync,
    OBJECT_PT_blendsync,
)

def register():
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)    
   

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    

