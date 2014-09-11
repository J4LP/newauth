import datetime
from flask import render_template, redirect, url_for, flash, current_app, request, session
from flask.ext.login import current_user, login_user, login_required
from flask.ext.classy import FlaskView, route
from newauth.eveapi import AuthenticationException
from newauth.forms import LoginForm, AccountUpdateForm, APIKeyForm
from newauth.models import db, User, APIKey
from newauth.models.enums import CharacterStatus
from newauth.utils import flash_errors


class AccountView(FlaskView):

    @login_required
    def index(self):
        return render_template('account/index.html')

    @route('profile', methods=['GET', 'POST'])
    @login_required
    def profile(self):
        account_form = AccountUpdateForm(obj=current_user)
        account_form.main_character.choices = [(character.id, character.name) for character in current_user.characters if character.get_status() != CharacterStatus.ineligible]
        if account_form.validate_on_submit():
            if account_form.new_password.data and not account_form.password.data:
                flash('Your password is required to make these changes.', 'danger')
                return redirect(url_for('AccountView:profile'))
            if current_user.check_password(account_form.password.data):
                # Password checks out, let's update it
                current_user.update_password(account_form.new_password.data)
                db.session.add(current_user)
                db.session.commit()
                User.password_updated.send(current_app._get_current_object(), model=current_user, password=account_form.new_password.data)
                ip = session['ip']
                session.clear()
                session['ip'] = ip
                flash('Your password has been updated, please login again.')
                return redirect(url_for('AccountView:login'))
            current_user.email = account_form.email.data
            new_main_character = current_user.characters.filter_by(id=account_form.main_character.data).first()
            if not character:
                flash("We could not found this character in your characters.", 'danger')
                return redirect(url_for('AccountView:profile'))
            else:
                current_user.name = new_main_character.name
                current_user.main_character_id = new_main_character.id
            db.session.add(current_user)
            db.session.commit()
            flash('Account updated.', 'success')
            return redirect(url_for('AccountView:profile'))
        api_forms = [APIKeyForm(obj=api_key) for api_key in current_user.api_keys]
        new_api_form = APIKeyForm()
        return render_template('account/profile.html', account_form=account_form, api_forms=api_forms, new_api_form=new_api_form)

    @route('update_api', methods=['POST'])
    @login_required
    def update_api(self):
        try:
            current_user.update_keys()
            current_user.update_status()
            db.session.add(current_user)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception(e)
            flash('Error updating your account.', 'danger')
        else:
            flash('Account updated with success!', 'success')
        return redirect(url_for('AccountView:profile'))

    @route('new_api', methods=['POST'])
    @login_required
    def new_api(self):
        form = APIKeyForm()
        if form.validate_on_submit():
            api_key = APIKey()
            form.populate_obj(api_key)
            try:
                api_key.update_api_key()
                api_key.validate(save=False)
            except AuthenticationException:
                flash('Could not authenticate with this API Key', 'danger')
                return redirect(url_for('AccountView:profile'))
            except Exception as e:
                flash('Error updating API Key: {}'.format(e.message), 'danger')
                return redirect(url_for('AccountView:profile'))
            else:
                current_user.api_keys.append(api_key)
                db.session.add(current_user)
                try:
                    db.session.commit()
                except Exception as e:
                    flash('We could not save your API Key in the database.', 'danger')
                    return redirect(url_for('AccountView:profile'))
                else:
                    current_user.update_keys()
                    current_user.update_status()
                    db.session.commit()
            flash('API Key added with success.', 'success')
        else:
            flash_errors(form)
        return redirect(url_for('AccountView:profile'))

    @route('update_api/<int:key_id>', methods=['POST'])
    @login_required
    def edit_api(self, key_id):
        form = APIKeyForm()
        if form.validate_on_submit():
            api_key = current_user.api_keys.filter_by(key_id=key_id).first()
            if not api_key:
                flash('We could not find the API Key #{} in your account.'.format(key_id), 'danger')
            else:
                api_key.key_id = form.key_id.data
                api_key.vcode = form.vcode.data
                try:
                    api_key.update_api_key()
                    api_key.validate(save=False)
                except AuthenticationException:
                    flash('Could not authenticate with this API Key', 'error')
                    return redirect(url_for('AccountView:profile'))
                except Exception as e:
                    flash('Error updating API Key: {}'.format(e.message), 'danger')
                    return redirect(url_for('AccountView:profile'))
                else:
                    db.session.add(api_key)
                    db.session.commit()
                    current_user.update_keys()
                    current_user.update_status()
                    flash('API Key updated.', 'success')
        else:
            flash_errors(form)
        return redirect(url_for('AccountView:profile'))

    @route('delete_api/<int:key_id>', methods=['POST'])
    @login_required
    def delete_api(self, key_id):
        api_key = current_user.api_keys.filter_by(key_id=key_id).first()
        if not api_key:
            flash('We could not find the API Key #{} in your account.'.format(key_id), 'danger')
        else:
            for character in api_key.characters.all():
                db.session.delete(character)
            db.session.commit()
            db.session.delete(api_key)
            db.session.commit()
            current_user.update_keys()
            current_user.update_status()
            flash('API Key deleted.', 'success')
        return redirect(url_for('AccountView:profile'))

    @route('login', methods=['GET', 'POST'])
    def login(self):
        if not current_user.is_anonymous():
            return redirect(url_for('AccountView:index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(user_id=form.user_id.data.lower()).first()
            if not user or not user.check_password(form.password.data):
                current_app.logger.warning('Invalid login with user_id "{}"'.format(form.user_id.data.lower()))
                User.login_fail.send(current_app._get_current_object(), user=user)
                flash('Invalid credentials.', 'danger')
                return redirect(url_for('AccountView:login'))
            if login_user(user):
                user.last_login_on = datetime.datetime.utcnow()
                user.last_ip = request.remote_addr
                User.login_success.send(current_app._get_current_object(), user=user)
                db.session.add(user)
                db.session.commit()
                if not user.main_character:
                    # It can happens
                    flash('You were able to login but we could not find a valid main character. Please update your account.', 'warning')
                    return redirect(url_for('AccountView:profile'))
                flash('Welcome back {}!'.format(user.main_character.name))
                return redirect(url_for('AccountView:index'))
            else:
                if not user.active:
                    flash('Your account is inactive.', 'danger')
                else:
                    flash('Your credentials were valid but we could not log you in.', 'danger')
                return redirect(url_for('AccountView:login'))
        return render_template('account/login.html', form=form)

    def logout(self):
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('AccountView:login'))
