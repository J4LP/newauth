from flask import render_template, flash, current_app, redirect, url_for, session, request
from flask.ext.classy import FlaskView, route
from slugify import slugify
from newauth.eveapi import AuthenticationException
from newauth.forms import APIKeyForm, RegisterForm
from newauth.models import APIKey, User, db
from newauth.models.enums import CharacterStatus


class RegisterView(FlaskView):

    def index(self):
        return render_template('register/index.html')

    @route('api', methods=['GET', 'POST'])
    def api(self):
        registration_type = request.args.get('type')
        if not registration_type or registration_type not in current_app.config['EVE']['requirements']:
            flash('Invalid registration type.', 'danger')
            return redirect(url_for('RegisterView:index'))
        form = APIKeyForm()
        if form.validate_on_submit():
            api_key = APIKey(key_id=form.key_id.data, vcode=form.vcode.data)
            try:
                api_key.update_api_key()
            except AuthenticationException:
                flash('Could not authenticate with this API Key', 'danger')
                return redirect(url_for('RegisterView:api', type=registration_type))
            except Exception as e:
                flash('Error updating API Key: {}'.format(e.message), 'danger')
                return redirect(url_for('RegisterView:api', type=registration_type))
            else:
                if api_key.mask != current_app.config['EVE']['requirements'][registration_type]['mask']:
                    flash('Wrong mask for API Key, needed {}, got {}'.format(current_app.config['EVE']['requirements'][registration_type]['mask'], api_key.mask), 'danger')
                    return redirect(url_for('RegisterView:api', type=registration_type))
                if current_app.config['EVE']['requirements'][registration_type]['expires'] and not api_key.mask:
                    flash('API Key should not have an expiration set. Please create another API Key.', 'danger')
                    return redirect(url_for('RegisterView:api', type=registration_type))
                flash('API Key accepted.', 'success')
                session['key_id'] = api_key.key_id
                session['vcode'] = api_key.vcode
                session['registration_type'] = registration_type
                return redirect(url_for('RegisterView:characters'))
        return render_template('register/api.html', form=form, registration_type=registration_type)

    def characters(self):
        try:
            key_id = session.get('key_id')
            vcode = session.get('vcode')
            registration_type = session.get('registration_type')
        except KeyError:
            flash('No API Key found in session.', 'danger')
            return redirect(url_for('RegisterView:index'))

        api_key = APIKey(key_id=key_id, vcode=vcode)
        try:
            api_key.update_api_key()
            acceptable_characters = set()
            for character in api_key.get_characters():
                status = character.get_status()
                if status == CharacterStatus.internal or status == CharacterStatus.ally:
                    acceptable_characters.add(character)
        except Exception as e:
            current_app.logger.exception(e)
            session.clear()
            flash('Could not fetch Character list: {}'.format(e.message))
            return redirect(url_for('RegisterView:api'))
        print(acceptable_characters)
        if not acceptable_characters:
            flash('We could not find any acceptable characters for you to register with.', 'danger')
            return redirect(url_for('RegisterView:index'))
        elif len(acceptable_characters) == 1:
            session['character'] = next(iter(acceptable_characters)).id
            return redirect(url_for('RegisterView:password'))
        else:
            return render_template('register/characters.html', api_key=api_key)

    @route('password', methods=['GET', 'POST'])
    def password(self):
        character_id = session['character']
        key_id = session['key_id']
        vcode = session['vcode']
        api_key = APIKey(key_id=key_id, vcode=vcode)
        api_key.update_api_key()
        for character in api_key.get_characters():
            if character.id == character_id:
                break
        else:
            flash('Character #{} not found in API Key #{}, aborting.'.format(character_id, key_id), 'danger')
            return redirect(url_for('RegisterView:index'))
        form = RegisterForm()
        form.user_id.data = slugify(character.name, to_lower=True, separator='_')
        if form.validate_on_submit():
            user = User(
                user_id=form.user_id.data,
                name=character.name,
                email=form.email.data,
                main_character_id=character.id
            )
            user.api_keys.append(api_key)
            user.update_password(form.password.data)
            for character in api_key.get_characters():
                user.characters.append(character)
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.exception(e)
                db.session.rollback()
                flash("Could not save user to database.", "danger")
            else:
                # Signals for registration
                User.new_user.send(current_app._get_current_object(), model=user, password=form.password.data)
                user.update_keys()
                user.update_status()
                session.clear()
                flash("Account created! Login now with {} and get started!".format(user.user_id), 'success')
                return redirect(url_for('AccountView:login'))
        return render_template('register/password.html', form=form, character=character)
