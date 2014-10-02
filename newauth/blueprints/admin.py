from flask import render_template, redirect, url_for, flash, current_app, request, session, abort, jsonify
from flask.ext.login import current_user, login_user, login_required
from flask.ext.classy import FlaskView, route
from flask.ext.sqlalchemy import Pagination
from newauth.eveapi import AuthenticationException
from newauth.forms import AccountAdminUpdateForm, APIKeyForm
from newauth.models import User, db, APIKey, Character
from newauth.models.enums import CharacterStatus
from newauth.utils import flash_errors, is_admin


class AdminView(FlaskView):

    decorators = [login_required, is_admin]

    def users(self):
        page = int(request.args.get('page', 1))
        users = User.query
        if request.args.get('user_id'):
            users = users.filter(User.user_id.ilike('%' + request.args.get('user_id') + '%'))
        if request.args.get('name'):
            users = users.filter(User.name.ilike('%' + request.args.get('name') + '%'))
        if request.args.get('corporation'):
            users = users.filter(User.main_character.has(Character.corporation_name.ilike('%' + request.args.get('corporation') + '%')))
        if request.args.get('alliance'):
            users = users.filter(User.main_character.has(Character.alliance_name.ilike('%' + request.args.get('alliance') + '%')))
        if request.args.get('status'):
            if request.args.get('status') != 'any':
                users = users.filter(User.status == CharacterStatus[request.args.get('status')].value)
        users = users.order_by(User.name).paginate(page)
        return render_template(
            'admin/users.html',
            users=users,
            user_id=request.args.get('user_id'),
            name=request.args.get('name'),
            corporation=request.args.get('corporation'),
            alliance=request.args.get('alliance'),
            status=request.args.get('status'),
        )

    @route('/users/<user_id>', methods=['GET', 'POST'])
    def admin_user(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            abort(404)
        if request.form.get('delete', None) == 'true' and current_user != user:
            try:
                for membership in user.groups.all():
                    db.session.delete(membership)
                db.session.flush()
                for character in user.characters.all():
                    db.session.delete(character)
                db.session.flush()
                for api_key in user.api_keys.all():
                    db.session.delete(api_key)
                db.session.commit()
            except Exception as e:
                current_app.logger.exception(e)
                db.session.rollback()
                flash('There was an issue deleting user\'s relations', 'danger')
                return redirect(url_for('AdminView:users'))
            db.session.delete(user)
            try:
                User.deletion.send(current_app._get_current_object(), user_id=user.user_id)
            except Exception as e:
                current_app.logger.exception(e)
                flash('There was an issue during the propagation of the deletion (LDAP, etc...)', 'danger')
            else:
                try:
                    db.session.commit()
                except Exception as e:
                    current_app.logger.exception(e)
                    db.session.rollback()
                    flash('We could not delete the user from NewAuth database.', 'danger')
                else:
                    flash('User deleted with success', 'success')
            return redirect(url_for('AdminView:users'))
        account_admin_form = AccountAdminUpdateForm(obj=user)
        account_admin_form.main_character.choices = [(character.id, character.name) for character in user.characters if character.get_status() != CharacterStatus.ineligible]
        if account_admin_form.validate_on_submit():
            user.email = account_admin_form.email.data
            new_main_character = user.characters.filter_by(id=account_admin_form.main_character.data).first()
            if not new_main_character:
                flash("Main character not found in user's characters.", 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user_id))
            user.main_character_id = new_main_character.id
            if account_admin_form.new_password.data:
                user.update_password(account_admin_form.new_password.data)
                User.password_updated.send(current_app._get_current_object(), model=user, password=account_admin_form.new_password.data)
            db.session.add(user)
            db.session.commit()
            flash("User saved.", 'success')
            return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
        api_forms = [APIKeyForm(obj=api_key) for api_key in user.api_keys]
        new_api_form = APIKeyForm()
        return render_template('admin/admin_user.html', user=user, account_admin_form=account_admin_form, api_forms=api_forms, new_api_form=new_api_form)

    @route('/users/<user_id>/update', methods=['POST'])
    def update_user(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            abort(404)
        try:
            user.update_keys()
            user.update_status()
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception(e)
            flash('Error updating user\'s account.', 'danger')
        else:
            flash('Account updated with success!', 'success')
        return redirect(url_for('AdminView:admin_user', user_id=user.user_id))

    @route('/users/<user_id>/add_key', methods=['POST'])
    def add_user_apikey(self, user_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            abort(404)
        form = APIKeyForm()
        if form.validate_on_submit():
            api_key = APIKey()
            form.populate_obj(api_key)
            try:
                api_key.update_api_key()
                api_key.validate(save=False)
            except AuthenticationException:
                flash('Could not authenticate with this API Key', 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            except Exception as e:
                flash('Error updating API Key: {}'.format(e.message), 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            user.api_keys.append(api_key)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                flash('We could not save your API Key in the database.', 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            else:
                user.update_keys()
                user.update_status()
                flash('API Key updated.', 'success')
        else:
            flash_errors(form)
        return redirect(url_for('AdminView:admin_user', user_id=user.user_id))

    @route('/users/<user_id>/edit_key/<int:key_id>', methods=['POST'])
    def edit_user_apikey(self, user_id, key_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            abort(404)
        form = APIKeyForm()
        if form.validate_on_submit():
            api_key = user.api_keys.filter_by(key_id=key_id).first()
            if not api_key:
                flash("We could not find the API Key #{} in this account.".format(key_id), 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            api_key.key_id = form.key_id.data
            api_key.vcode = form.vcode.data
            try:
                api_key.update_api_key()
                api_key.validate(save=False)
            except AuthenticationException:
                flash('Could not authenticate with this API Key', 'error')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            except Exception as e:
                flash('Error updating API Key: {}'.format(e.message), 'danger')
                return redirect(url_for('AdminView:admin_user', user_id=user.user_id))
            else:
                db.session.add(api_key)
                db.session.flush()
                user.update_keys()
                user.update_status()
                db.session.commit()
                flash("API Key updated.", 'success')
        return redirect(url_for('AdminView:admin_user', user_id=user.user_id))

    @route('/users/<user_id>/delete_key/<int:key_id>', methods=['POST'])
    def delete_user_apikey(self, user_id, key_id):
        user = User.query.filter_by(user_id=user_id).first()
        if not user:
            abort(404)
        api_key = user.api_keys.filter_by(key_id=key_id).first()
        if not api_key:
            flash("We could not find the API Key #{} in this account.".format(key_id), 'danger')
        for character in api_key.characters.all():
            db.session.delete(character)
        db.session.delete(api_key)
        db.session.flush()
        user.update_keys()
        user.update_status()
        db.session.commit()
        flash("API Key deleted.", 'success')
        return redirect(url_for('AdminView:admin_user', user_id=user.user_id))

