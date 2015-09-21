#!/usr/bin/env python
# -*- coding: utf-8 -*-


from flask import render_template, request, redirect, \
    url_for, flash, session, abort
from flask.blueprints import Blueprint
from flask.ext.babel import gettext
from flask.ext.login import current_user, login_user, logout_user, \
    login_required
from sqlalchemy.exc import OperationalError
from ldap3 import LDAPCommunicationError

from model import dormitory_from_name, user_from_ip, unsupported_dormitories
from model.default import BaseUser

from sipa.forms import flash_formerrors, LoginForm, AnonymousContactForm
from sipa.utils import current_user_name
from sipa.utils.exceptions import UserNotFound, PasswordInvalid
from sipa.utils.mail_utils import send_mail


import logging
logger = logging.getLogger(__name__)

bp_generic = Blueprint('generic', __name__)


@bp_generic.before_app_request
def log_request():
    # handler = SentryHandler(current_app.config['SENTRY_DSN'])
    # THIS IS KEY!!! – if uncommented, logging to
    # getLogger().addHandler(handler)

    logging.getLogger(__name__ + '.http').debug(
        'Incoming request: %s %s', request.method, request.path,
        extra={'tags': {'user': current_user_name(),
                        'ip': request.remote_addr}}
    )


@bp_generic.app_errorhandler(401)
@bp_generic.app_errorhandler(403)
@bp_generic.app_errorhandler(404)
def error_handler_redirection(e):
    """Handles errors by flashing an according message
    :param e: The error
    :return: A flask response with the according HTTP error code
    """
    if e.code == 401:
        message = gettext("Bitte melde Dich an, um die Seite zu sehen.")
    elif e.code == 403:
        message = gettext("Diese Funktion wird in deinem Wohnheim "
                          "nicht unterstützt.")
    elif e.code == 404:
        message = gettext("Das von Dir angeforderte Dokument gibt es nicht.")
    else:
        message = gettext("Es ist ein Fehler aufgetreten!")
    return render_template(
        'error.html',
        errorcode=e.code,
        message=message
    ), e.code


@bp_generic.app_errorhandler(OperationalError)
def exceptionhandler_sql(ex):
    """Handles global MySQL errors (server down).
    """
    flash(gettext("Verbindung zum SQL-Server konnte nicht "
                  "hergestellt werden!"),
          "error")
    logger.critical('Unable to connect to MySQL server',
                    extra={'data': {'exception_args': ex.args}})
    return redirect(url_for('generic.index'))


@bp_generic.app_errorhandler(LDAPCommunicationError)
def exceptionhandler_ldap(ex):
    """Handles global LDAPCommunicationError exceptions.
    The session must be reset, because if the user is logged in and the server
    fails during his session, it would cause a redirect loop.
    This also resets the language choice, btw.

    The alternative would be a try-except catch block in load_user, but login
    also needs a handler.
    """
    session.clear()
    flash(gettext(
        "Verbindung zum LDAP-Server konnte nicht hergestellt werden!"),
        "error"
    )
    logger.critical(
        'Unable to connect to LDAP server',
        extra={'data': {'exception_args': ex.args}}
    )
    return redirect(url_for('generic.index'))


@bp_generic.route("/language/<string:lang>")
def set_language(lang='de'):
    """Set the session language via URL
    """
    session['locale'] = lang
    return redirect(request.referrer)


@bp_generic.route('/index.php')
@bp_generic.route('/')
def index():
    return redirect(url_for('news.display'))


@bp_generic.route("/login", methods=['GET', 'POST'])
def login():
    """Login page for users
    """
    form = LoginForm()

    if form.validate_on_submit():
        dormitory = dormitory_from_name(form.dormitory.data)
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        User = dormitory.datasource.user_class

        try:
            user = User.authenticate(username, password)
        except (UserNotFound, PasswordInvalid):
            flash(gettext("Anmeldedaten fehlerhaft!"), "error")
        else:
            if isinstance(user, User):
                session['dormitory'] = dormitory.name
                login_user(user, remember=remember)
                logger.info('Authentication successful')
                flash(gettext("Anmeldung erfolgreich!"), "success")
    elif form.is_submitted():
        flash_formerrors(form)

    if current_user.is_authenticated:
        return redirect(url_for('usersuite.usersuite'))

    return render_template('login.html', form=form,
                           unsupported=unsupported_dormitories)


@bp_generic.route("/logout")
@login_required
def logout():
    logger.info('Logging out')
    logout_user()
    return redirect(url_for('.index'))


@bp_generic.route("/usertraffic")
def usertraffic():
    """For anonymous users with a valid IP
    """
    ip_user = user_from_ip(request.remote_addr)

    if isinstance(ip_user, BaseUser):
        if current_user.is_authenticated:
            if current_user != ip_user:
                flash(gettext("Ein anderer Nutzer als der für diesen "
                              "Anschluss Eingetragene ist angemeldet!"),
                      'warning')
                flash(gettext("Hier werden die Trafficdaten "
                              "dieses Anschlusses angezeigt"), "info")

        return render_template("usertraffic.html", usertraffic=(
            ip_user.get_traffic_data()))
    else:
        if current_user.is_authenticated:
            return render_template("usertraffic.html", usertraffic=(
                current_user.get_traffic_data()))
        else:
            abort(401)


@bp_generic.route('/contact', methods=['GET', 'POST'])
def contact():
    form = AnonymousContactForm()

    if form.validate_on_submit():
        from_mail = form.email.data
        subject = "[Kontakt] {}".format(form.subject.data)
        message = form.message.data
        dormitory = dormitory_from_name(form.dormitory.data)
        support_mail = dormitory.datasource.support_mail

        if send_mail(from_mail, support_mail, subject, message):
            flash(gettext("Nachricht wurde versandt."), "success")
        else:
            flash(gettext("Es gab einen Fehler beim Versenden der Nachricht."),
                  'error')
        return redirect(url_for(".index"))
    elif form.is_submitted():
        flash_formerrors(form)

    return render_template('anonymous_contact.html', form=form)
