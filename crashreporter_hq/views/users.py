import flask.ext.login as flask_login
from flask import request, render_template, flash, redirect, url_for

from .. import app, db
from ..forms import CreateAliasForm, PasswordChangeform
from ..models import User, Alias, UUID


@app.route('/users', methods=['GET'])
@flask_login.login_required
def users():
    if request.method == 'GET':
        uid = int(request.args.get('id', -1))
        if uid and flask_login.current_user.id == uid:
            # Show profile for the logged in user
            return redirect(url_for('user_profile'))
        elif uid < 0:
            if flask_login.current_user.admin:
                user_list = User.query.all()
                return render_template('users.html', user_list=user_list, user=flask_login.current_user)
            else:
                return 'Admin access only.'


@app.route('/users/profile', methods=['GET'])
@flask_login.login_required
def user_profile():
    if request.method == 'GET':
        password_change_form = PasswordChangeform()
        return render_template('user_profile.html', user=flask_login.current_user, pw_form=password_change_form)


@app.route('/users/profile/update_password', methods=['POST'])
@flask_login.login_required
def update_password():
    if request.method == 'POST':
        alias_form = CreateAliasForm()
        password_change_form = PasswordChangeform()
        if password_change_form.validate_on_submit() and flask_login.current_user.password == password_change_form.old_password.data:
            flask_login.current_user.password = password_change_form.new_password.data
            flash('Your password has been successfully changed.')
            db.session.commit()

        return render_template('user_profile.html', user=flask_login.current_user,
                               alias_form=alias_form, pw_form=password_change_form)

