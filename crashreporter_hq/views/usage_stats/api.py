import json
import flask_login
import flask
from flask import request
from sqlalchemy import func

from ...models import Statistic, State, Timer, Sequence, UUID, User, Application, Group
from ... import app, db


TRACKABLES = {'Statistic': Statistic,
              'State': State,
              'Timer': Timer,
              'Sequence': Sequence}

TRACKABLE_ATTRS = {'Statistic': {'value': Statistic.count, 'sum': func.sum(Statistic.count)},
                    'State':    {'value': State.state,     'sum': func.count(State.state)},
                    'Timer':    {'value': Timer.time,      'sum': func.sum(Timer.count)},
                    'Sequence': {'value': Sequence.count,  'sum': func.sum(Sequence.count)}
                  }


@app.route('/usagestats/upload', methods=['POST'])
def upload_stats():
    payload = json.loads(request.data)
    api_key = payload.get('API Key')

    if api_key is None:
        return 'Missing API Key.'
    user = User.query.filter(User.api_key == api_key).first()
    if user is None:
        return 'Upload failed'
    elif user.group is None:
        return 'User does not belong to a group.'
    else:
        for trackable_name, data in payload.get('Data', {}).iteritems():
            cls = TRACKABLES.get(data['type'])
            # Get the UUID row or create one if it doesn't exist
            uuid = UUID.query.filter(UUID.user_identifier==payload['User Identifier']).first()
            if uuid is None:
                # Create the UUID row if it doesn't already exist
                uuid = UUID(payload['User Identifier'])
                uuid.group.append(user.group)
                db.session.add(uuid)

            # Parse the application version into a tuple
            app_version = payload['Application Version'].split('.')
            q = Application.query.filter(Application.name == payload['Application Name'])
            for ii, v in enumerate(app_version):
                q.filter(getattr(Application, 'version_%d' % ii) == int(v))
            application = q.first()

            if application is None:
                # Create the Application row if it doesn't already exist
                application = Application(payload['Application Name'], app_version)
                db.session.add(application)
                db.session.commit()

            trackable = cls.query.filter(cls.name == trackable_name,
                                         cls.application_id == application.id,
                                         cls.uuid_id == uuid.id,
                                         cls.group_id == user.group_id).first()
            if trackable is None:
                trackable = cls(trackable_name, uuid, application, user.group)
                db.session.add(trackable)
            # Apply the value of the data to the row
            if data['type'] == 'State':
                trackable.state = data['data']
            else:
                trackable.count = data['data']
        db.session.commit()
        return 'Success'


def _filter_trackables(q, trackable_class, **filters):
    if 'uuid' in filters:
        q = q.filter(UUID.user_identifier==filters['uuid'])
    if 'application' in filters:
        q = q.filter(trackable_class.application_name==filters['application'])
    if 'trackable' in filters:
        q = q.filter(trackable_class.name == filters['trackable'])

    return q

@app.route('/usage/trackables', methods=['GET'])
def get_trackables():
    types = request.args.get('type', None)
    api_key = request.args.get('api_key', None)
    if api_key is None:
        flask.abort(flask.Response('You must provide a value for api_key', status=400))
    else:
        group_id, = db.session.query(User.group_id).filter(User.api_key == api_key).first()

    data = {}
    if types is None:
        types = TRACKABLES.keys()
    else:
        types = types.split(',')

    for t in types:
        t = t.capitalize()
        cls = TRACKABLES[t.capitalize()]
        attr = TRACKABLE_ATTRS[t.capitalize()]['value']
        q = db.session.query(cls.name, Application.name, UUID.user_identifier, attr).join(UUID, Application)
        q = _filter_trackables(q, cls, **{k: v for k, v in request.args.iteritems()})
        q.filter(cls.group_id==group_id)
        data[t] = q.all()

    return flask.jsonify(data)


@app.route('/usage/trackables/<trackable_type>', methods=['GET'])
def get_statistics(trackable_type):
    sortby = request.args.get('sortby', None)
    trackable = request.args.get('trackable', None)
    api_key = request.args.get('api_key', None)
    if api_key is None:
        flask.abort(flask.Response('You must provide a value for api_key', status=400))
    else:
        group_id, = db.session.query(User.group_id).filter(User.api_key == api_key).first()

    cls = {'statistics': Statistic, 'timers': Timer, 'sequences': Sequence}.get(trackable_type)
    if cls is None:
        flask.abort(400)

    data = {}

    if sortby == 'application':
        # return list of (trackable name, cummulative value) keyed by application name
        sort_query = db.session.query(Application.name)\
                                .distinct()\
                                .filter(Application.group_id==group_id)
        for app_name, in sort_query:

            q = db.session.query(cls.name, func.sum(cls.count)) \
                          .join(cls.application) \
                          .filter(Application.name==app_name) \
                          .group_by(cls.name)\

            if trackable:
                q = q.filter(cls.name==trackable)
            data[app_name] = q.all()

    elif sortby == 'uuid':
        # return list of (trackable name, cummulative value) keyed by UUID
        sort_query = db.session.query(UUID.user_identifier)\
                               .distinct()\
                               .filter(UUID.group_id==group_id)

        for user_id, in sort_query:
            q = db.session.query(cls.name, func.sum(cls.count)) \
                          .join(cls.uuid) \
                          .filter(UUID.user_identifier==user_id) \

            if trackable:
                q = q.filter(cls.name==trackable)
            data[user_id] = q.all()

    else:
        # return list of (application name, cummulative value) keyed by trackable name
        if trackable is not None:
            sort_query = [(trackable,)]
        else:
            sort_query = db.session.query(cls.name) \
                                   .distinct() \
                                   .filter(cls.group_id == group_id)

        for tr, in sort_query:
            data[tr] = db.session.query(Application.name, func.sum(cls.count)) \
                                 .join(cls.application) \
                                 .filter(cls.name==tr) \
                                 .group_by(Application.name)\
                                 .all()
    return flask.jsonify(data)


@app.route('/usage/trackables/states', methods=['GET'])
def get_states():
    sortby = request.args.get('sortby', None)
    trackable = request.args.get('trackable', None)
    api_key = request.args.get('api_key', None)
    if api_key is None:
        flask.abort(flask.Response('You must provide a value for api_key', status=400))
    else:
        group_id, = db.session.query(User.group_id).filter(User.api_key == api_key).first()

    data = {}
    if sortby == 'application':
        # return list of (trackable name, state value, number of users) keyed by application name
        sort_query = db.session.query(Application.name) \
                               .distinct() \
                               .filter(Application.group_id == group_id)
        for app_name, in sort_query:

            q = db.session.query(State.name, State.state, func.count(State.state)) \
                          .join(State.application) \
                          .filter(Application.name == app_name) \
                          .group_by(State.name, State.state)

            if trackable:
                q = q.filter(State.name == trackable)
            data[app_name] = q.all()

    elif sortby == 'uuid':
        # return list of (trackable name, application name, state value) keyed by application name
        sort_query = db.session.query(UUID.user_identifier) \
                               .distinct() \
                               .filter(UUID.group_id == group_id)
        for user_id, in sort_query:

            q = db.session.query(State.name, Application.name, State.state) \
                          .join(State.uuid, State.application) \
                          .filter(UUID.user_identifier == user_id)
            if trackable:
                q = q.filter(State.name == trackable)
            data[user_id] = q.all()

    elif sortby == 'state':
        # return list of (trackable name, application name, number of users) keyed by state value
        if trackable is None:
            flask.abort(flask.Response('Must specify "trackable" when sorting by state', status=400))

        sort_query = db.session.query(State.state) \
                               .distinct() \
                               .filter(UUID.group_id == group_id, State.name == trackable)

        for state, in sort_query:

            q = db.session.query(State.name, Application.name, func.count(State.state)) \
                          .join(State.uuid, State.application) \
                          .filter(State.state == state)

            data[state] = q.all()

    elif sortby in (None, 'trackable'):
        # return list of (state value, application name, number of users) keyed by trackable name
        if trackable is not None:
            sort_query = [(trackable,)]
        else:
            sort_query = db.session.query(State.name) \
                                   .distinct() \
                                   .filter(State.group_id == group_id)

        for tr, in sort_query:
            data[tr] = db.session.query(State.state, Application.name, func.count(State.state)) \
                .join(State.application) \
                .filter(State.name == tr) \
                .group_by(Application.name, State.state) \
                .all()

    return flask.jsonify(data)