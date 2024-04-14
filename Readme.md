# BlendSync - Bleneder Add-on for synchronizing Objects and Devices via OSC

BlendSync allows to synchronize an arbitrary number of instances and OSC clients with close to zero configuration required! 

## Functionality in Blender

Blender instances connect to or launch a local service automatically when a synchronization action is taken. You can check the state and establish connections (also to remote locations) via the side-panel in the 3D view under Sync->SyncBlend. 

### BlendSync-Panel
The BlendSync-Panel is located in the object properties.

### Proxy-Objects Constraints

For known channels, BlendSync provides Proxy-Objects with the address as name and the properties assigned to the object. Configure the constraint to your liking and select the corresponding object to access the synchronization data.


### Nodes

**WIP**


### Deleting registered channels / Proxy-Objects

An operator can be found in the SyncBlend panel of the 3D side view to clear all proxy objects.


## Connect OSC clients

**Warning: Work in progress!!**

OSC clients can be connected via the local IP address of the host machine and the publish / client-to-server port (default is 8000). The back channel is available on port 7000, both can be configured in the side-panel of the host instance.

As soon as a OSC command has been received, BlendSync will add a proxy object where the name is the address, except the final part. This will be the name of the property and for common names like _location_, _rotation_, _scale_ these attributes are directly applied to the existing properties of the Blender object. The proxy objects can be used as described in _Functionality in Blender_.