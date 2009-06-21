import re

from routes import Mapper
from routes import request_config

_marker = object()

class RoutesRootFactory(Mapper):
    def __init__(self, default_root_factory, **kw):
        self.default_root_factory = default_root_factory
        kw['controller_scan'] = None
        kw['always_scan'] = False
        kw['directory'] = None
        kw['explicit'] = True
        Mapper.__init__(self, **kw)
        self._regs_created = False

    def has_routes(self):
        return bool(self.matchlist)

    def connect(self, *arg, **kw):
        result = Mapper.connect(self, *arg, **kw)
        route = self.matchlist[-1]
        route._factory = None # overridden by ZCML
        return result

    def __call__(self, environ):
        if not self._regs_created:
            self.create_regs([])
            self._regs_created = True
        path = environ.get('PATH_INFO', '/')
        self.environ = environ # sets the thread local
        match = self.routematch(path)
        if match:
            args, route = match
        else:
            args = None
        if isinstance(args, dict): # might be an empty dict
            args = args.copy()
            routepath = route.routepath
            config = request_config()
            config.mapper = self
            config.mapper_dict = args
            config.host = environ.get('HTTP_HOST', environ['SERVER_NAME'])
            config.protocol = environ['wsgi.url_scheme']
            config.redirect = None
            environ['wsgiorg.routing_args'] = ((), args)
            environ['bfg.routes.route'] = route
            environ['bfg.routes.matchdict'] = args
            # this is stolen from routes.middleware; if the route map
            # has a *path_info capture, use it to influence the path
            # info and script_name of the generated environment
            if 'path_info' in args:
                if not 'SCRIPT_NAME' in environ:
                    environ['SCRIPT_NAME'] = ''
                oldpath = environ['PATH_INFO']
                newpath = args['path_info'] or ''
                environ['PATH_INFO'] = newpath
                if not environ['PATH_INFO'].startswith('/'):
                    environ['PATH_INFO'] = '/' + environ['PATH_INFO']
                pattern = r'^(.*?)/' + re.escape(newpath) + '$'
                environ['SCRIPT_NAME'] += re.sub(pattern, r'\1', oldpath)
                if environ['SCRIPT_NAME'].endswith('/'):
                    environ['SCRIPT_NAME'] = environ['SCRIPT_NAME'][:-1]
            factory = route._factory or self.default_root_factory
            return factory(environ)

        return self.default_root_factory(environ)

