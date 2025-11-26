"""
This module exposes an RPyC Server subclass which should act as the
base class for all driver services.
"""
import rpyc

class Service(rpyc.Service):
    # See https://rpyc.readthedocs.io/en/latest/docs/security.html#attribute-access
    def _rpyc_getattr(self, name):
        if name.startswith("__"):
            # disallow special and private attributes
            raise AttributeError("cannot access private/special names")
        # allow all other attributes
        return getattr(self, name)
