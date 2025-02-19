"""
Basic utilities for the Flask app

These are basic utilities necessary for the Flask app which are
disjoint from any blueprint.
"""
from flask import request, session
from flask_login import AnonymousUserMixin
from werkzeug.routing import IntegerConverter as BaseIntegerConverter

from sipa.login_manager import SipaLoginManager
from sipa.backends import backends

login_manager = SipaLoginManager()
login_manager.login_view = "generic.login"


class IntegerConverter(BaseIntegerConverter):
    """IntegerConverter supporting negative values

    This is a Modification of the standard IntegerConverter which does
    not support negative values.  See the corresponding `werkzeug
    documentation
    <http://werkzeug.pocoo.org/docs/0.10/routing/#werkzeug.routing.IntegerConverter>`_.
    """
    regex = r'-?\d+'


@login_manager.user_loader
def load_user(username):
    """Loads a User object from/into the session at every request
    """
    dormitory = backends.get_dormitory(session.get('dormitory', None))
    if dormitory:
        return dormitory.datasource.user_class.get(username)
    else:
        return AnonymousUserMixin()
