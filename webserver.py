from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
import sre
import sys
import urllib
import urlparse

import emithtml


def parse_qs(string):
    query = cgi.parse_qs(string)
    result = {}
    for key in query:
	if len(query[key]) != 1:
	    raise 'Multiple values for key', key
	result[key] = query[key][0]
    return result

def make_query(uri, **kwargs):
    return '%s?%s' % (uri, urllib.urlencode(kwargs))


class AutorestartServer(HTTPServer):
    # XXX needs work

    def __init__(self, restart_filename, *args):
	self._restart_filename = restart_filename
	self._note_fresh()
        BaseHTTPServer.__init__(self, *args)

    def process_request(self, request, client_address):
	if self._is_stale():
	    self._restart()
	    self._note_fresh()
	return BaseHTTPSever.process_request(self, request, client_address)

    def _note_fresh(self):
	import os
	self._fresh_on = os.stat(self._restart_filename).st_mtime

    def _is_stale(self):
	import os
	mtime = os.stat(self._restart_filename).st_mtime
	return mtime != self._fresh_on

    def _restart(self):
        self.RequestHandlerClass = self._reload_request_handler_class()

    def _reload_request_handler_class(self):
	return FIXME


def make_dispatching_handler_class(dispatcher):

    class DispatchingHTTPRequestHandler(BaseHTTPRequestHandler):

	def do_GET(self):
	    self._handle(dispatcher.getters, parse_qs)

	def do_POST(self):
	    self._handle(dispatcher.posters, self._parse_post_params)

	def _parse_post_params(self, url_query_str):
	    content_length = int(self.headers.getheader('Content-Length'))
	    if content_length == 0:
		data = ''
	    else:
		data = self.rfile.read(content_length)
	    return parse_qs(data)

	def _handle(self, handlers, parse_query):
	    _, _, path_str, _, query_str, _ = urlparse.urlparse(self.path)
	    if path_str[0:1] == '/': # XXX does this ever not happen?
		path_str = path_str[1:]
	    handler, params = _lookup(handlers, path_str)
	    if handler is None:
		return self.reply_404()
	    try:
		query = parse_query(query_str)
		handler(self, *params, **query)
	    except:
		exception_type, exception_value = sys.exc_info()[:2]
		complaint = \
		    cgi.escape('%s: %s' % (exception_type, exception_value))
		self.reply(['Error: ' + complaint,
			    emithtml.P(),
			    repr(query)])
		print 'query_str = [', query_str, ']'
		raise

	def redirect(self, uri):
	    self.send_response(302, uri)
	    self.send_header('Location', uri)
	    self.send_header('Content-type', 'text/html')
	    self.end_headers() 
	    self.wfile.write('Redirect to <a href="%s">%s</a>' % (uri, uri))

	def reply(self, body_html):
	    self.send_response(200)
	    self.send_header('Content-type', 'text/html')
	    self.end_headers()
	    self.wfile.write(emithtml.emit(body_html))

	def reply_404(self):
	    self.send_error(404, 'Object not found: %s' % self.path)

    return DispatchingHTTPRequestHandler

def _lookup(pairs, path_str):
    for (name, pattern), handler in pairs:
	m = pattern.match(path_str)
	if m:
	    return handler, m.groups()
    return None, None

def parse_name(name):
    parts = name.split('_')
    patterns = [cond(part == 'V', r'([^/]+)', part) for part in parts]
    name = '/'.join(patterns) + '$'
    return name, sre.compile(name)

def cond(test, yes, no):
    if test: return yes
    return no


class MetaDispatcher:

    def __init__(self):
	self.getters = self._collect('get_')
	self.posters = self._collect('post_')

    def _collect(self, prefix):
	pairs = [(parse_name(name[len(prefix):]), getattr(self, name))
		 for name in dir(self) if name.startswith(prefix)]
	return tuple(pairs)
