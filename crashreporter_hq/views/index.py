import flask
from flask import Response

from datetime import datetime
from math import ceil
from sqlalchemy import or_, func

from ..models import CrashReport, Application

from users import *
from crashreports import report_to_json
from constants import *

import httplib
import operator


def filter_reports(criteria):
    user = flask_login.current_user
    group = user.group

    related_to_id = criteria.get('related_to_id', None)
    q = CrashReport.query
    q = q.join(Application).filter(CrashReport.group == group)

    # Filter aliased state
    aliased_state = criteria.get('alias_filter', ANY)
    if aliased_state == NONE:
        q = q.filter(CrashReport.uuid_id.notin_([a.uuid_id for a in group.aliases]))
    elif aliased_state == ONLY:
        q = q.filter(CrashReport.uuid_id.in_([a.uuid_id for a in group.aliases]))

    # Filter released state
    released_state = criteria.get('release_filter', ANY)
    if released_state == NONE:
        q = q.filter(Application.is_release == False)
    elif released_state == ONLY:
        q = q.filter(Application.is_release == True)

    if criteria.get('before_date'):
        date = datetime.strptime(criteria['before_date'], '%d/%m/%Y')
        q = q.filter(CrashReport.date <= date)
    if criteria.get('after_date'):
        date = datetime.strptime(criteria['after_date'], '%d/%m/%Y')
        q = q.filter(CrashReport.date >= date)

    search_fields, search_values = zip(*criteria.get('filters', [('', '')]))
    if any(search_values):
        for ii, (field, value) in enumerate(zip(search_fields, search_values)):
            if not value:
                continue

            if field == 'user_identifier':
                # Search the user identifiers associated with any aliases that may be part of the search
                conditions = [UUID.user_identifier.contains(a.user_identifier) for a in group.aliases if
                              value in a.alias]
                conditions.append(UUID.user_identifier.contains(value))
                logic_or = or_(*conditions)
                q = q.filter(logic_or).join(UUID)
            elif field == 'date':
                date = datetime.strptime(value, '%d %B %Y').strftime('%Y-%m-%d')
                q = q.filter(func.date(CrashReport.date) == date)
            elif field == 'application_name':
                q = q.filter(Application.name.contains(value))
            elif field in ('application_version', 'after_version', 'before_version'):
                v0, v1, v2 = map(int, value.split('.'))
                op = {'application_version': operator.eq,
                      'after_version': operator.ge,
                      'before_version': operator.le}[field]
                q = q.filter(op(Application.version_0, v0),
                             op(Application.version_1, v1),
                             op(Application.version_2, v2))
            elif field == 'report_count_gt':
                if related_to_id is None:
                    q = q.having(func.count(CrashReport.related_group_id) >= int(value))
            elif field == 'report_count_lt':
                if related_to_id is None:
                    q = q.having(func.count(CrashReport.related_group_id) <= int(value))
            else:
                attr = getattr(CrashReport, field)
                q = q.filter(attr.contains(str(value)))

    page = criteria.get('page', 1)
    n_per_page = criteria.get('reports_per_page')
    if related_to_id is None:
        n_users_affected = q.group_by(CrashReport.uuid_id).count()
        q = q.group_by('related_group_id')
    else:
        related_group_id = db.session.query(CrashReport.related_group_id).filter(CrashReport.id == int(related_to_id)).first()
        q = q.filter(CrashReport.related_group_id == related_group_id[0])
        n_users_affected = q.group_by(CrashReport.uuid_id).count()
    q = q.order_by(CrashReport.date.desc())
    n_reports = q.count()
    max_page = int(ceil(float(n_reports) / n_per_page))
    reports = q[n_per_page * (page-1):n_per_page * page: -1]
    response = {'reports': [],
                'page': page,
                'max_page': max_page or 1,
                'n_users_affected': n_users_affected,
                'total_reports': n_reports}
    aliases = {a.user_identifier: a.alias for a in group.aliases}

    for r in reports:
        response['reports'].append(report_to_json(r, aliases=aliases))
    json = flask.jsonify(response)
    return json


@app.route('/', methods=['GET'])
@flask_login.login_required
def view_reports():
    html = render_template('index.html', user=flask_login.current_user)
    return html


# This search view is needed because there doesn't seem to be a way to get the pagination links to update
# the page number while maintaining the search form.
@app.route('/search', methods=['POST'])
@flask_login.login_required
def search():
    if flask_login.current_user.group:
        form_data = request.get_json()
        return filter_reports(form_data)
    else:
        r = Response()
        r.status_code = httplib.FORBIDDEN
        r.data = 'Invalid access. You must log in first.'
