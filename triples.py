class SemanticNet:

    def __init__(self):
	self.facts = {}

    def _rep_invariant(self):
	pass			# TODO

    def delete_subject(self, subject):
	del self.facts[subject]

    def set_subject(self, subject, pairs):
	self.facts[subject] = tuple(pairs)

    def find_subject(self, subject):
	"""Return a list of all triples with the given subject value."""
	return [(subject, pair[0], pair[1],) 
		for pair in self.facts.get(subject, ())]

    def find_predicate(self, predicate):
	"""Return a list of all triples with the given predicate value."""
	result = []
	for subject in self.facts:
	    for a_predicate, an_object in self.facts[subject]:
		if a_predicate == predicate:
		    result.append((subject, a_predicate, an_object,))
	return result

    def find_object(self, object):
	"""Return a list of all triples with the given object value."""
	result = []
	for subject in self.facts:
	    for a_predicate, an_object in self.facts[subject]:
		if an_object == object:
		    result.append((subject, a_predicate, an_object,))
	return result

    def query(self, dict, qtriples):
	"""Return a list of dicts extending 'dict' to match all the query
	triples 'qtriples' conjointly."""
	if len(qtriples) == 0:
	    return [dict]
	result = []
	for dict2 in self.query_triple(dict, qtriples[0]):
	    result.extend(self.query(dict2, qtriples[1:]))
	return result

    def query_triple(self, dict, qtriple):
	"""Return a list of dicts extending 'dict' to match the query
	'qtriple'."""
	result = []
	qsubject = qtriple.maybe_constant_subject(dict)
	if qsubject is not None:
	    self._query_subject(result, dict, qtriple, qsubject)
	else:
	    for subject in self.facts:
		self._query_subject(result, dict, qtriple, subject)
	return result

    def _query_subject(self, result, dict, qtriple, subject):
	"""Add to result the matches from qtriple against my triples with the
	given subject."""
	for predicate, object in self.facts.get(subject, ()):
	    dict2 = qtriple.match(dict, (subject, predicate, object,))
	    if dict2 is not None:
		result.append(dict2)

class QueryTriple:

    def __init__(self, triple):
	self.triple = triple

    def maybe_constant_subject(self, dict):
	return self.triple[0].maybe_constant(dict)

    def add_variables(self, variables):
	for element in self.triple:
	    element.add_variables(variables)

    def match(self, dict, triple):
	"""Return dict extended with the result of matching me against
	'triple', or None if no match.  Does not mutate the original
	dict."""
	return match1(self.triple[0], triple[0], 
		      match1(self.triple[1], triple[1],
			     match1(self.triple[2], triple[2],
				    dict)))

def match1(query1, link1, dict):
    if dict is None:
	return None
    return query1.match(dict, link1)


class Literal:

    def __init__(self, value):
	self.value = value

    def maybe_constant(self, dict):
	return self.value

    def add_variables(self, variables):
	pass

    def match(self, dict, value):
	if self.value == value:
	    return dict
	return None

class Variable:

    def __init__(self, name):
	self.name = name

    def maybe_constant(self, dict):
	if self.name in dict:
	    return dict[self.name]
	return None
	
    def add_variables(self, variables):
	if self.name not in variables:
	    variables.append(self.name)

    def match(self, dict, value):
	if self.name in dict:
	    if dict[self.name] == value:
		return dict
	    return None
	result = dict.copy()
	result[self.name] = value
	return result

def identity(x): 
    return x

class QueryMaker:
    def __init__(self):
	self.make_triple = QueryTriple
	self.make_literal = Literal
	self.make_variable = Variable

class DataMaker:
    def __init__(self):
	self.make_triple = identity
	self.make_literal = identity
	self.make_variable = identity


# Triple syntax
# XXX integrate this with the rest of the program
# XXX probably a lot shorter with regexes

class Parser:

    def __init__(self, input, maker):
	self.input = input
	self.r = input
	self.maker = maker

    def _eat_blanks(self):
	self.r = self.r.lstrip()

    def _eat(self, punctuation):
	self._eat_blanks()
	if punctuation == self.r[:1]:
	    self.r = self.r[1:]
	else:
	    # TODO: show place in full input
	    raise 'Expected %s at %s in %s' % (punctuation, self.r, self.input)

    def done(self):
	self._eat_blanks()
	if '' != self.r:
	    raise 'Premature end', self.input

    def parse_triples(self):
	self._eat_blanks()
	if ']' == self.r[:1]:	# XXX abstraction leak
	    return ()
	triple = self.parse_triple()
	self._eat_blanks()
	if not self._more_triples():
	    rest = ()
	else:
	    self._eat(',')
	    rest = self.parse_triples()
	return (triple,) + rest

    def _more_triples(self):
	return ',' == self.r[:1]

    def parse_triple(self):
	subject   = self.parse_term()
	predicate = self.parse_term()
	object    = self.parse_term()
	return self.maker.make_triple((subject, predicate, object,))

    def parse_pair(self):
	predicate = self.parse_term()
	object    = self.parse_term()
	if self.r.strip() != '':
	    raise 'Bad pair syntax', self.input
	return predicate, object

    def parse_term(self):
	self._eat_blanks()
	if '' == self.r:	# XXX check for ']' too (ugh)
	    return ''  # XXX raise 'Missing term', self.input
	if self.r.startswith('['):
	    return self.parse_quoted_string()
	return self.parse_word()

    def parse_word(self):
	delim = charset_find(self.r, ' \t\r\n,]') # XXX ] is an abs leak
	if 0 == delim:
	    return ''  # XXX raise 'Missing term', self.input
	word = self.r[:delim]
	self.r = self.r[delim:]
	if word.islower():
	    term = self.maker.make_literal(word)
	else:
	    term = self.maker.make_variable(word)
	return term

    def parse_quoted_string(self):
	q = ''
	self.r = self.r[1:]
	while True:
	    j = charset_find(self.r, '\\]')
	    if len(self.r) == j:
		raise 'Unterminated string', self.input
	    q = q + self.r[:j]
	    if '\\' == self.r[j:j+1]:
		q = q + self.r[j+1:j+2]
		self.r = self.r[j+2:]
	    else:
		self.r = self.r[j+1:]
		return self.maker.make_literal(q)

def charset_find(s, chars):
    for i in range(len(s)):
	if s[i] in chars:
	    return i
    return len(s)


# Top-level facade

def parse_qtriples(string):
    p = Parser(string, QueryMaker())
    qtriples = p.parse_triples()
    p.done()
    return qtriples

def parse_pair(string):
    p = Parser(string, DataMaker())
    pair = p.parse_pair()
    p.done()
    return pair


# Tests
# From Kragen Sitaker's DHTML triple-store

#         assert(is_var("A"), "A")
#         assert(!is_var("a"), "a")
#         assert(is_var("Ax"), "Ax")
#         assert(!is_var("xA"), "xA")
#         assert(is_var("Z"), "Z")

def try_query(ts, input, expected):
    qtriples = parse_qtriples(input)
    output = ts.query({}, qtriples)
    if output != expected:
	raise 'Unexpected result', (input, output, expected,)

def test_me():
    ts = SemanticNet()
    no = []
    yes = [{}]

    ts.set_subject('a', (('b','c',),))

    try_query(ts, '', yes)
    try_query(ts, 'a b c', yes)
    try_query(ts, 'a b d', no)
    try_query(ts, 'a b c, a b c', yes)
    try_query(ts, 'a b c, a b d', no)
    try_query(ts, 'a b d, a b d', no)
    try_query(ts, 'a b d, a b c', no)
    try_query(ts, 'a b X', [{'X': 'c'}])
    try_query(ts, 'a X c', [{'X': 'b'}])
    try_query(ts, 'X b c', [{'X': 'a'}])
    try_query(ts, 'a X d', no)
    try_query(ts, 'a X Y', [{'X': 'b', 'Y': 'c'}])
    try_query(ts, 'a X X', no)
    try_query(ts, 'A B C', [{'A': 'a', 'B': 'b', 'C': 'c'}])

    ts.delete_subject('a')
    ts.set_subject('a', (('b','c',), ('b', 'e',),))
    ts.set_subject('same', (('c','c',),))

    try_query(ts, 'a b c', yes)
    try_query(ts, 'a b c, a b e', yes)
    try_query(ts, 'a b e, a b c', yes)
    try_query(ts, 'a b d, a b c', no)
    try_query(ts, 'A B C', [
	{'A': 'a',    'B': 'b', 'C': 'c'},
	{'A': 'a',    'B': 'b', 'C': 'e'},
	{'A': 'same', 'B': 'c', 'C': 'c'},
    ])
    try_query(ts, 'A B C, A b c', [
	{'A': 'a', 'B': 'b', 'C': 'c'},
	{'A': 'a', 'B': 'b', 'C': 'e'}])
    try_query(ts, 'a b X', [{'X': 'c'}, {'X': 'e'}])
    try_query(ts, 'X Y Y', [{'X': 'same', 'Y': 'c'}])
    try_query(ts, 'A B C, X C Y', [
	{'A': 'a', 'B': 'b', 'C': 'c', 'X': 'same', 'Y': 'c'},
	{'A':"same", 'B':"c", 'C':"c", 'X':"same", 'Y':"c"}])
