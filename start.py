#!/usr/bin/env python

from BaseHTTPServer import HTTPServer

import doss


server = None

def start(mainmodule):
    global server
    server = HTTPServer(('', 8082), mainmodule.MyHTTPRequestHandler)
    print 'started httpserver...'
    serve()

def serve():
    server.serve_forever()

def snap(mainmodule, snapshot):
    import os
    # XXX raises an exception in Windows if oldsnapshot exists
    # XXX should never overwrite old snapshots
    name = snapshot.__name__
    # mainmodule.upgrade()
    os.rename(name + '.py', 'old' + name)
    doss.serialize(mainmodule.get_system(), 
		   mainmodule.get_module_names_used_persistently(),
		   file(name + '.py', 'w'))

def main(mainmodule, snapshot):
    mainmodule.set_system(snapshot.root)
    # import changes		# XXX temporary
    try:
	try:
	    start(mainmodule)
	except KeyboardInterrupt:
	    print '^C received, shutting down server'
	    server.socket.close()
    finally:
	snap(mainmodule, snapshot)


if __name__ == '__main__':
    import sys
    mainmodule = __import__(sys.argv[1])
    snapshot = __import__(sys.argv[2])
    main(mainmodule, snapshot)
