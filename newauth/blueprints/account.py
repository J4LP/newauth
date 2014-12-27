import datetime
import hashlib
from flask import render_template, redirect, url_for, flash, current_app, request, session
from flask.ext.classy import FlaskView, route
from flask.ext.login import current_user, login_user, login_required
from flask.ext.mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from newauth.app import mail
from newauth.eveapi import AuthenticationException
from newauth.forms import LoginForm, AccountUpdateForm, APIKeyForm, AccountRecoverForm, AccountDoRecoveryForm
from newauth.models import db, User, APIKey, redis
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
        account_form.main_character.default = current_user.main_character_id
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
                return form.redirect('AccountView:index')
            else:
                if not user.active:
                    flash('Your account is inactive.', 'danger')
                else:
                    flash('Your credentials were valid but we could not log you in.', 'danger')
                return redirect(url_for('AccountView:login'))
        return render_template('account/login.html', form=form)

    def logout(self):
        current_ip = session.get('ip')
        session.clear()
        session['ip'] = current_ip
        flash('You have been logged out.', 'info')
        return redirect(url_for('AccountView:login'))

    @route('recover', methods=['GET', 'POST'])
    def recover(self):
        form = AccountRecoverForm()
        if form.validate_on_submit():
            user = User.query.filter((User.user_id == form.user_id.data) | (User.email == form.email.data)).first()
            if not user:
                flash('We could not find this user in our database.', 'warning')
                return redirect(url_for('AccountView:recover'))
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            recover_key = serializer.dumps({'recover': True, 'user_id': user.user_id})
            at_index = user.email.rfind('@')
            obfuscated_email = user.email[0:3] + ('*' * (at_index - 3)) + user.email[at_index:]
            message = Message(
                subject='Account recovery on {} auth'.format(current_app.config['EVE']['auth_name']),
                recipients=[user.email],
                html=render_template('emails/account_recover.html', recovery_link=url_for('AccountView:do_recovery', recover_key=recover_key, _external=True), auth_name=current_app.config['EVE']['auth_name'])
            )
            try:
                mail.send(message)
            except Exception as e:
                current_app.logger.exception(e)
                flash('NewAuth was not able to send an email out. Please contact an administrator.', 'danger')
            else:
                flash('We have sent an email to {} with instructions to recover your account.'.format(obfuscated_email), 'success')
            return redirect(url_for('AccountView:login'))
        return render_template('account/recover.html', form=form)

    @route('recover/<recover_key>', methods=['GET', 'POST'])
    def do_recovery(self, recover_key):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        md5_encoder = hashlib.md5()
        md5_encoder.update(recover_key)
        recover_key_md5 = md5_encoder.hexdigest()
        if redis.get('recovery:{}'.format(recover_key_md5)):
            flash('This recovery key has already been used.', 'danger')
            return redirect(url_for('AccountView:login'))
        try:
            recovery_data = serializer.loads(recover_key, 60 * 60 * 24)
        except SignatureExpired:
            flash('This recovery key has expired, please start the recovery process again.', 'danger')
            return redirect(url_for('AccountView:login'))
        except BadSignature:
            flash('Invalid recovery key.', 'danger')
            return redirect(url_for('AccountView:login'))
        if not recovery_data.get('recover', False):
            flash('Invalid payload.', 'danger')
            return redirect(url_for('AccountView:login'))
        user = User.query.filter_by(user_id=recovery_data['user_id']).first()
        if not user:
            flash('User not found for recovery.', 'danger')
            return redirect(url_for('AccountView:login'))
        form = AccountDoRecoveryForm()
        if form.validate_on_submit():
            user.update_password(form.password.data)
            User.password_updated.send(current_app._get_current_object(), model=user, password=form.password.data)
            redis.set('recovery:{}'.format(recover_key_md5), True)
            redis.expire('recovery:{}'.format(recover_key_md5), 60 * 60 * 24)
            flash('Account password changed.', 'success')
            return redirect(url_for('AccountView:login'))
        return render_template('account/do_recovery.html', user=user, recover_key=recover_key, form=form)
