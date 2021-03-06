from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, SelectField, BooleanField, Label
from wtforms.validators import DataRequired, EqualTo, Email
from views.constants import *

class LoginForm(Form):
    email = StringField('email', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])


class PasswordChangeform(Form):
    old_password = PasswordField('old_password', validators=[DataRequired()])
    new_password = PasswordField('new_password', validators=[DataRequired()])
    confirm = PasswordField('confirm', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])


class SignUpForm(Form):
    email = StringField('email', validators=[DataRequired(), Email()])
    password = PasswordField('password', validators=[DataRequired()])
    confirm = PasswordField('confirm', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    name = StringField('name')
    company = StringField('name')


class SearchForm(Form):
    name = StringField('name')
    submit = SubmitField('Search')


class CreateGroupForm(Form):
    name = StringField('name')
    description = TextAreaField('desc')
    submit = SubmitField('Create')


class PlotCreationForm(Form):
    name = StringField('name')
    fields = StringField('fields')
    submit = SubmitField('Create')


class AddReleaseForm(Form):
    name = StringField('name')
    version = StringField('fields')
    submit = SubmitField('Add')


class SearchReportsForm(Form):
    choices = [('user_identifier', 'User'), ('application_name', 'Application Name'),
               ('application_version', 'Application Version'), ('after_version', 'After Version'),
               ('before_version', 'Before Version'), ('id', 'Report Number'),
               ('error_message', 'Error Message'), ('error_type', 'Error Type'),
               ('date', 'Date'), ('before_date', 'Before Date'), ('after_date', 'After Date')]
    field1 = SelectField(choices=choices, default='user')
    value1 = StringField('Value')

    field2 = SelectField(choices=choices, default='application_name')
    value2 = StringField('Value')

    field3 = SelectField(choices=choices, default='application_version')
    value3 = StringField('Value')

    fields = field1, field2, field3
    values = value1, value2, value3

    hide_aliased_label = Label('hide_aliased_label', 'Aliases:')
    hide_aliased = SelectField(choices=[(str(ANY), '----'),
                                        (str(NONE), 'No Aliases'),
                                        (str(ONLY), 'Only Aliases')])

    releases_only_label = Label('releases_only_label', 'Versions:')
    releases_only = SelectField(choices=[(str(ANY), '----'),
                                         (str(NONE), 'Non-Released Versions'),
                                         (str(ONLY), 'Released Versions')])


class CreateAliasForm(Form):
    alias = StringField('alias', validators=[DataRequired()])
    uuid = StringField('uuid', validators=[DataRequired()])
    submit = SubmitField('Create')


class YoutrackSubmitForm(Form):
    server = StringField('YouTrack Server', validators=[DataRequired()])
    project = StringField('Project', validators=[DataRequired()])
    assignee = StringField('Assignee', validators=[DataRequired()])
    summary = StringField('Summary', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    priority = StringField('Priority')
    type = StringField('Type')
    subsystem = StringField('Subsystem')
    state = StringField('State')
    affects_versions = StringField('Affects_versions')
    permitted_group = StringField('Permitted Group')
    submit = SubmitField("Submit")