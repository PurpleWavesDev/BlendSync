# BlendSync - Bleneder Add-on for synchronizing Objects and Devices via OSC
# Developed by Kira Vogt

bl_info = {
        "name": "BlendSync",
        "description": "Sync properties of objects through OSC between Blender Instances and external software",
        "author": "Kira Vogt",
        "version": (0, 1, 0),
        "blender": (4, 0, 0),
        "location": "3D View > Sidebar > Sync",
        "warning": "",
        "wiki_url": "",
        "tracker_url": "",
        "support": "COMMUNITY",
        "category": "System"
        }

import bpy    

def checkDependencies():
    # Check dependencies and install if needed
    import pip
    try: import zmq
    except: pip.main(['install', 'pyzmq', '--user', '--no-warn-script-location'])
    
    try: import oscpy
    except: pip.main(['install', 'oscpy', '--user', '--no-warn-script-location'])



def register():
    checkDependencies()
    
    from . import properties, network, sync, ui
    properties.register()
    network.register()
    sync.register()
    ui.register()

def unregister():
    from . import properties, network, sync, ui
    ui.unregister()
    sync.unregister()
    network.unregister()
    properties.unregister()


if __name__ == '__main__':
    register()
    