import rpyc
from rpyc import Service
import io
import sys

class MyService(Service):
    def exposed_execute(self, code):
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        try:
            exec(code)
            return captured_output.getvalue()
        except Exception as e:
            return f"Error: {e}"
        finally:
            sys.stdout = old_stdout

if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    server = ThreadedServer(MyService, port=18812)
    print("Servidor rpyc corriendo en puerto 18812")
    server.start()