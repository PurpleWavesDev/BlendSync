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
    bl_label = "Scene" 
    bl_idname = "VIEW3D_PT_blendsync" 
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        wm_syncprops = context.window_manager.blendsync
        
        # Connection status and OPs
        split = layout.split(factor=0.4)
        split.label(text="Server")
        split.prop(wm_syncprops, 'server_addr', text="")
        split = layout.split(factor=0.4)
        split.label(text="Port")
        split.prop(wm_syncprops, 'server_port', text="")
        row = layout.row()
        row.operator(BLENDSYNC_OT_connect.bl_idname, icon ="PLUS")
        

class OBJECT_PT_blendsync(Panel):
    """Panel in the object properties for blendsync"""
    bl_idname = 'OBJECT_PT_blendsync'
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_label = "BlendSync"
    bl_context = "object"
    
    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        obj = context.object
        wm_syncprops = context.window_manager.blendsync

        # Frame List
        row = layout.row()
        row.label("Send")
        row = layout.row()
        row.label("Receive")



# -------------------------------------------------------------------
# un/register
# -------------------------------------------------------------------

classes =(
    VIEW3D_PT_blendsync,
)

def register():
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)    
   

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    

