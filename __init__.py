# Blender Stop Motion Virtual Production Extension
# Kira Vogt

bl_info = {
        "name": "BlendSync",
        "description": "Sync properties of objects through OSC between Blender Instances and external software",
        "author": "Kira Vogt",
        "version": (0, 1, 0),
        "blender": (4, 0, 0),
        "location": "3D View > Sidebar > ??",
        "warning": "",
        "wiki_url": "",
        "tracker_url": "",
        "support": "COMMUNITY",
        "category": "System"
        }

import bpy    

def checkDependencies():
    # Check dependencies and install if needed
    try:
        import zmq
    except:
        import pip
        pip.main(['install', 'pyzmq', '--user'])



def register():
    checkDependencies()
    
    from . import client, properties, sync, ui
    properties.register()
    client.register()
    sync.register()
    ui.register()

def unregister():
    from . import client, properties, sync, ui
    ui.unregister()
    sync.unregister()
    client.unregister()
    properties.unregister()


if __name__ == '__main__':
    register()
    