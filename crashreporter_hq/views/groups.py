

import flask
from flask import request, render_template, flash, redirect, url_for
from sqlalchemy import func
import flask.ext.login as flask_login

from .. import app, db
from ..forms import CreateGroupForm, SearchForm, CreateAliasForm, PlotCreationForm, AddReleaseForm
from ..models import Group, User, UUID, CrashReport, Alias, StatisticBarPlot, Statistic, State, Timer, Application
from ..models.trackables import TrackableTables


@app.route('/groups', methods=['GET', 'POST'], defaults={'group': None})
@app.route('/groups/<string:group>', methods=['GET', 'POST'])
@flask_login.login_required
def groups(group):
    sform = SearchForm(prefix='search')
    cform = CreateGroupForm(prefix='create')
    alias_form = CreateAliasForm()
    plot_form = PlotCreationForm()
    release_form = AddReleaseForm()

    if request.method == 'GET':
        if group is None:
            g = flask_login.current_user.group
        else:
            g = Group.query.filter(Group.name == group).first()
            if g is None:
                flash('Group "{name}" does not exist.'.format(name=group))
                g = flask_login.current_user.group

        if flask_login.current_user.group_admin:
            uuids = g.uuids
        else:
            uuids = []
        if g:
            trackables = {'statistics': db.session.query(Statistic, func.count(Statistic.id)).filter(Statistic.group_id==g.id).group_by(Statistic.name).all(),
                          'states': db.session.query(State, func.count(State.id)).filter(State.group_id==g.id).group_by(State.name).all(),
                          'timer': db.session.query(Timer, func.count(Timer.id)).filter(Timer.group_id==g.id).group_by(Timer.name).all(),
                         }
        else:
            trackables = {}
        return render_template('groups.html', sform=sform, cform=cform, release_form=release_form, alias_form=alias_form, plot_form=plot_form,
                                group=g, user=flask_login.current_user, uuids=uuids, trackables=trackables)

    elif cform.validate_on_submit() and cform.data['submit']:
        # Creating a group
        group = Group.query.filter(Group.name == cform.data['name']).first()
        if group is None:
            g = Group(cform.data['name'], description=cform.data['description'])
            user = flask_login.current_user
            user.group = g
            user.group_admin = True
            db.session.add(g)
            db.session.commit()
            flash('Group "{name}" has been created.'.format(**cform.data))
            return redirect(url_for('groups'))
        else:
            flash('Group "{name}" already exists.'.format(**cform.data))
            return redirect(url_for('groups'))
    elif sform.validate_on_submit() and sform.data['submit']:
        # Searching for a group
        return redirect(url_for('groups', group=sform.data['name']))


@app.route('/groups/request/join', methods=['POST'])
@flask_login.login_required
def group_join_request():
    group = request.args['group']
    loggedin_user = flask_login.current_user
    if loggedin_user.group.name == group and loggedin_user.group_admin:
        g = Group.query.filter(Group.name == group).first()
        q = User.query.filter(User.email == request.args['user_email'])
        u = q.first()
        if u in g.join_requests:
            g.join_requests.remove(u)
            g.join_requests_id = None
            db.session.commit()
            if request.args['action'] == 'accept':
                u.group = g
                db.session.commit()
            return redirect(url_for('groups', group=group))


@app.route('/groups/members', methods=['get'])
@flask_login.login_required
def get_group_members():
    group = flask_login.current_user.group
    if group is None:
        return 'You are not in a group.'
    users = User.query.filter(User.group_id == group.id).all()
    data = {u.id: {'name': u.name, 'email': u.email, 'group_admin': u.group_admin} for u in users}
    return flask.jsonify(data)


@app.route('/groups/members/<int:user_id>', methods=['POST'])
@flask_login.login_required
def manage_member(user_id):
    loggedin_user = flask_login.current_user
    if not loggedin_user.group_admin:
        flask.abort(403)

    group = loggedin_user.group

    u = User.query.filter(User.id == user_id, User.group_id == group.id).first()
    if u:
        if request.args['action'] == 'remove':
            group.users.remove(u)
            u.group = None
            u.group_admin = False
        elif request.args['action'] == 'promote':
            u.group_admin = True
        elif request.args['action'] == 'demote':
            u.group_admin = False
        db.session.commit()
        return redirect(url_for('groups', group=group))


@app.route('/groups/request/request_invite', methods=['POST'])
@flask_login.login_required
def request_group_invite():
    # Current user has requested to join the group
    group = request.args['group']
    loggedin_user = flask_login.current_user
    if loggedin_user.group is None or (group != loggedin_user.group.name):
        g = Group.query.filter(Group.name == group).first()
        # Only request to join the group is the user isn't already in a group
        if flask_login.current_user not in g.join_requests:
            g.join_requests.append(flask_login.current_user)
            db.session.commit()
            flash('Request to join group "{name}" has been submitted.'.format(name=group))
        else:
            flash('Request to join group "{name}" has already been submitted.'.format(name=group))
        return redirect(url_for('groups', group=group))


@app.route('/uuids/<int:uuid_id>', methods=['POST'])
@flask_login.login_required
def manage_uuid(uuid_id):
    uuid = UUID.query.filter(UUID.id == uuid_id).first()
    if request.method == 'POST' and uuid:
        if request.args.get('action') == 'toggle_usage_stats':
            uuid.usagestats_black_listed = not uuid.usagestats_black_listed
            db.session.commit()
        elif request.args.get('action') == 'toggle_crash_reports':
            uuid.crashreport_black_listed = not uuid.crashreport_black_listed
            db.session.commit()
        elif request.args.get('action') == 'delete':
            for table in TrackableTables[:] + [CrashReport, Alias]:
                n_deleted = table.query.filter(table.uuid_id==uuid_id).delete()
                print n_deleted, table.__class__.__name__
            db.session.delete(uuid)
            db.session.commit()

    return redirect(request.referrer)