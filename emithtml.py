import cgi


def emit(obj, attribute=False):
    if type(obj) == list:
	return ''.join([emit(element) for element in obj])
    if type(obj) == str:
	return cgi.escape(obj, attribute)
    if type(obj) == type(emit):
	return obj()		# XXX what if attribute=True?
    raise 'Bad type', obj

def emit_attributes(dict):
    attrs = []
    for key in dict:
	attrs.append(' %s="%s"' % (cgi.escape(key), 
				   emit(dict[key], attribute=True)))
    return ''.join(attrs)

def make_tag_emitter(tag):
    def make(_='', **kwargs):
	def emitter():
	    return '<%s%s>%s</%s>' % (tag,
				      emit_attributes(kwargs), emit(_),
				      tag)
	return emitter
    return make

def make_lonetag_emitter(tag):
    def make(**kwargs):
	def emitter():
	    return '<%s%s>' % (tag, emit_attributes(kwargs))
	return emitter
    return make

A        = make_tag_emitter('a')
Form     = make_tag_emitter('form')
H1       = make_tag_emitter('h1')
H2       = make_tag_emitter('h2')
H3       = make_tag_emitter('h3')
I        = make_tag_emitter('i')
Li       = make_tag_emitter('li')
Pre      = make_tag_emitter('pre')
Table    = make_tag_emitter('table')
TextArea = make_tag_emitter('textarea')
Tbody    = make_tag_emitter('tbody')
Td       = make_tag_emitter('td')
Th       = make_tag_emitter('th')
Thead    = make_tag_emitter('thead')
Tr       = make_tag_emitter('tr')
# XXX Tr and Td should leave out the closing tag
Ul       = make_tag_emitter('ul')

Br       = make_lonetag_emitter('br')
Input    = make_lonetag_emitter('input')
P        = make_lonetag_emitter('p')
Hr       = make_lonetag_emitter('hr')
