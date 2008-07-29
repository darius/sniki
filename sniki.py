import cgi
import sre
import time

from emithtml import A, Br, Form, H2, Hr, I, Input, Li, P, Pre, \
    Table, Tbody, Td, Th, Thead, TextArea, Tr, Ul
import triples
import webserver


# The data model and the persistent root.

root = None

def set_system(system):
    global root
    root = system		# Assumed to be a sniki.Root
    root._rep_invariant()

def get_system():
    return root

def get_module_names_used_persistently():
    return ('sniki',)


class Root:

    def __init__(self, pages=None):
	self.pages = pages
	self.triples = triples.SemanticNet()
	for page in pages:
	    self._update_store(page)
	
    def uneval(self, context, label):
	return context.uncall('sniki.Root',
			      pages=self.pages)

    def _rep_invariant(self):
	_check_list_of_class(Page, self.pages)
	_check_each_rep_invariant(self.pages)
	self.triples._rep_invariant()

    def _update_store(self, page):
	self.triples.set_subject(page.title, page.parse_links())

    def get_page(self, title):
	for page in self.pages:
	    if page.title == title:
		return page
	raise KeyError, title

    def add_page(self, title):
	page = Page(title, '', '', '', None)
	self.pages.append(page)
	self._update_store(page)
	return page

    # Added to support changes.py -- not needed normally
    def update_page(self, page):
	self._update_store(page)
	for i in range(len(self.pages)):
	    if self.pages[i].title == page.title:
		self.pages[i] = page
		return
	self.pages.append(page)


class Page:

    def __init__(self, title, body, links_text, pre_text, last_update=None):
	self.title = title
	self.body = body
	self.set_links(links_text)
        self.pre_text = pre_text
        self.last_update = last_update

    def uneval(self, context, label):
	return context.uncall('sniki.Page',
			      title=self.title,
			      body=self.body,
			      links_text=self.links_text,
                              pre_text=self.pre_text,
                              last_update=self.last_update)

    def _rep_invariant(self):
	assert type(self.title) == str
	assert type(self.body) == str
	assert type(self.links_text) == str
	assert type(self.pre_text) == str
	assert self.last_update is None or type(self.last_update) == str

    def mark_update(self):
        self.last_update = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def log(self):
	# XXX quick hack
	import doss
	doss.serialize(self, ('sniki',), file('changes.py', 'a'))
	
    def set_links(self, links_text):
	self.links_text = links_text

    def parse_links(self):
	pairs = []
	for line in self.links_text.split('\n'):
	    if '' == line or line.isspace():
		continue
	    pairs.append(triples.parse_pair(line))
	return pairs

    def show_links(self):
	foo = root.triples.find_subject(self.title)
	bar = root.triples.find_predicate(self.title)
	baz = root.triples.find_object(self.title)
	return intersperse(map(self.show_link, foo + bar + baz), Br())

    def show_link(self, llink):
	if llink:
	    return [self.show_key(llink[0]),
		    ' ',
		    self.show_key(llink[1]),
		    ' ',
		    self.show_key(llink[2])]

    def show_key(self, key):
	if key == self.title:
	    return key
	return link('/page/' + key, key)

    def show(self):
	return [link('/edit/' + self.title, 'edit'),
                ' | ', link('Recent Changes', 'recent'),
                H2(self.title), html_format(self.body),
		Hr(), self.show_links(),
                Hr(), Pre(self.pre_text),
		]

    def show_edit(self):
	# XXX url encoding of title
	return [H2(self.title),
		Form(method='POST', action='/update/' + self.title,
		     _=[submit('Save'),
			TextArea(name='body', style='width:100%', rows='30',
				 _=self.body),
			'Links:',
			TextArea(name='links', style='width:100%', rows='10',
				 _=self.links_text),
                        'Pre:',
                        TextArea(name='pre_text',
                                 style='width:100%', rows='10',
                                 _=self.pre_text),
                        ])
		]


pat_paragraph = r'\r?\n\r?\n'
pat_uri       = r'http:[^ \r\n()]+' # XXX make this more accurate
pat_tabulate  = r'\[tabulate\s'
pat_slink     = r'\[[^\]]+\]'		  # simple link
pat_escape    = r'\\.'
pat_token     = '|'.join([pat_paragraph, pat_uri, pat_tabulate, pat_slink,
			  pat_escape])
def html_format(src):
    out = []
    while src != '':
	m = sre.search(pat_token, src)
	if m is None:
	    break
	out.append(src[:m.start()])
	token = src[m.start():m.end()]
	src = src[m.end():]
	if sre.match(pat_paragraph, token):
	    out.append(P())
	elif sre.match(pat_uri, token):
	    out.append(link(token, token))
	elif sre.match(pat_tabulate, token):
	    qtriples, src = parse_tabulate(src)
	    tabulate(out, qtriples)
	elif sre.match(pat_slink, token):
	    contents = token[1:-1].split()
	    if 0 == len(contents):
		pass			     # XXX error message?
	    else:
		# XXX security screen target and caption
		# (caption should not look like a URL itself)
		# XXX url encoding
		# XXX nofollow
		if contents[0].startswith('http:'):
		    target = contents[0]	     
		    if 1 == len(contents):
			caption = contents[0]
		    else:
			caption = ' '.join(contents[1:])
		else:
		    caption = ' '.join(contents)
		    target = '/page/' + caption
	    out.append(link(target, caption)) 
	elif sre.match(pat_escape, token):
	    out.append(token[1])
	else:
	    raise 'Bug'
    out.append(src)
    return out

def tabulate(out, qtriples):
    variables = get_variables(qtriples)
    rows = do_queries(variables, qtriples)
    output_table(out, variables, rows)

def do_queries(variables, qtriples):
    return [[dict[v] for v in variables] 
	    for dict in root.triples.query({}, qtriples)]


def output_table(out, variables, rows):
    head = Thead(Tr([Th(align='left', _=v) for v in variables]))
    body = Tbody([Tr([Td(A(href=value, _=value) )
		      for value in row]) 
		  for row in rows])
    html = Table([head, body])
    out.append(html)


def get_variables(qtriples):
    variables = []
    for qt in qtriples:
	qt.add_variables(variables)
    return variables

def parse_tabulate(src):
    p = triples.Parser(src, triples.QueryMaker())
    qtriples = p.parse_triples()
    p._eat(']')
    return qtriples, p.r


# The web UI

class SnikiDispatcher(webserver.MetaDispatcher):

    def get_(self, http):
	http.redirect('/page/sniki')

    def get_V(self, http, filename):
	if 'robots.txt' != filename:
	    http.reply_404()
	    return
	http.send_response(200)
	http.send_header('Content-type', 'text/plain')
	http.end_headers()
	http.wfile.write('''User-agent: *
Disallow:   /edit/
''')

    def show_recent_changes(self):
        pages = [p for p in root.pages if p.last_update is not None]
        pages.sort(lambda p1, p2:
                     -cmp(p1.last_update, p2.last_update))
        lines = [[p.last_update, ' ', link(p.title, p.title)]
                 for p in pages]
	return [H2('Recent Changes'),
                Ul([Li(line) for line in lines])
                ]
    
    def get_page_V(self, http, name):
	name = urldecode(name)
        if 'Recent Changes' == name:
            http.reply(self.show_recent_changes())
            return
	try:
	    page = root.get_page(name)
	except KeyError:
	    http.redirect('/edit/' + name)
	    return
	http.reply(page.show())

    def get_edit_V(self, http, name):
	name = urldecode(name)
	try:
	    page = root.get_page(name)
	except KeyError:
	    page = root.add_page(name)
	http.reply(page.show_edit())

    def post_update_V(self, http, name, body='', links='', pre_text=''):
	name = urldecode(name)
	try:
	    page = root.get_page(name)
	except KeyError:
	    http.reply_404()
	    return
	page.body = body
	page.set_links(links)
        page.pre_text = pre_text
	root._update_store(page)
        page.mark_update()
	page.log()
	http.redirect('/page/' + name)


MyHTTPRequestHandler = \
	webserver.make_dispatching_handler_class(SnikiDispatcher())


def urldecode(encoded):
    ugh = cgi.parse_qs('x=' + encoded)
    sheesh = ugh['x'][0]	# XXX
    return sheesh

def link(link, body):
    return A(href=link, _=body)

def hidden(name, value):
    return Input(type='hidden', name=name, value=str(value))

def submit(value, name=None):
    if name is None:
	return Input(type='submit', value=str(value))
    else:
	return Input(type='submit', name=name, value=str(value))

def intersperse(elements, tween):
    result = []
    if 0 < len(elements):
	result.append(elements[0])
    for e in elements[1:]:
	result.append(tween)
	result.append(e)
    return result

def _check_each_rep_invariant(sequence):
    for element in sequence:
	element._rep_invariant()

def _check_list_of_class(klass, sequence):
    assert type(sequence) == list
    for element in sequence:
	assert klass == element.__class__
