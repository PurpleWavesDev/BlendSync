from subprocess import Popen
import socket
import zmq
import time

# Globals
process = None
    
def LaunchServer(port=0) -> bool:
    """Launches the server process"""
    global process
    
    process = Process(target=Server.run)
    # Launch process
    try:
        process.start()
        return True
    except Exception as e:
        print(f"Error: Can't launch server process ({str(e)})")
    return False

def StopServer():
    """Stops the server"""
    global process
    
    if process:
        process.terminate()


class Server:
    def run():
        while True:
            time.sleep(0.1)

