import datetime
from flask import render_template, abort, request, jsonify, redirect, url_for, flash
from flask.ext.classy import FlaskView, route
from flask.ext.login import current_user, login_required
from newauth.forms import GroupCreateForm, GroupEditForm, GroupApplicationForm
from newauth.models import Group, GroupMembership, db
from newauth.models.enums import GroupType
from newauth.utils import flash_errors, is_admin


class GroupsView(FlaskView):

    decorators = [login_required]

    def index(self):
        groups = Group.query.all()
        new_group_form = GroupCreateForm()
        new_group_form.type.choices = [(element.name, element.value) for element in list(GroupType)]
        return render_template('groups/index.html', groups=groups, new_group_form=new_group_form)

    @route('/new', methods=['POST'])
    @is_admin
    def new_group(self):
        new_group_form = GroupCreateForm()
        new_group_form.type.choices = [(element.name, element.value) for element in list(GroupType)]
        if new_group_form.validate_on_submit():
            group = Group()
            new_group_form.populate_obj(group)
            group.type = GroupType[new_group_form.type.data].value
            membership = GroupMembership(user=current_user, group=group, is_admin=True, can_ping=True)
            db.session.add(group)
            db.session.add(membership)
            db.session.commit()
            flash("Group '{}' created with success.".format(group.name), 'success')
        else:
            flash_errors(new_group_form)
        return redirect(url_for('GroupsView:index'))

    @route('/<name>', methods=['GET', 'POST'])
    def get(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user_id=current_user.id).first()
        if not membership:
            flash('You are not a member of this group.', 'danger')
            return redirect(url_for('GroupsView:index'))
        group_edit_form = GroupEditForm(obj=group)
        group_edit_form.type.choices = [(element.name, element.value) for element in list(GroupType)]
        if current_user.is_admin_of(group):
            if group_edit_form.validate_on_submit():
                pass
        return render_template('groups/group.html', group=group, membership=membership, group_edit_form=group_edit_form)

    @route('/join', methods=['GET', 'POST'])
    def join(self):
        group_id = request.form.get('group_id')
        if not group_id:
            abort(400)
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            abort(404)
        membership = GroupMembership(user=current_user, group=group)
        membership.joined_on = datetime.datetime.utcnow()
        db.session.add(membership)
        db.session.commit()
        flash("You have joined the group '{}'".format(group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))



    @route('/<name>/apply', methods=['GET', 'POST'])
    def apply(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user_id=current_user.id).first()
        if membership:
            if membership.is_applying:
                flash("You have already applied to this group.", 'warning')
            else:
                flash("You are already a member of this group.", 'warning')
            return redirect(url_for('GroupsView:index'))
        group_application_form = GroupApplicationForm()
        if group_application_form.validate_on_submit():
            membership = GroupMembership(
                group=group,
                user=current_user,
                is_applying=True,
                applied_on=datetime.datetime.utcnow()
            )
            membership.application_text = group_application_form.application_text.data
            db.session.add(membership)
            db.session.commit()
            flash("Application received.", 'success')
            return redirect(url_for('GroupsView:get', name=group.name))
        return render_template('groups/application.html', group=group, group_application_form=group_application_form)

    @route('/<name>/retract_application', methods=['POST'])
    def retract_application(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user_id=current_user.id).first()
        if not membership:
            flash("We could not find your application to this group.", 'warning')
            return redirect(url_for('GroupsView:index'))
        if not membership.is_applying:
            flash("You have already been accepted to this group.", 'warning')
            return redirect(url_for('GroupsView:index'))
        db.session.delete(membership)
        db.session.commit()
        flash("Your application to '{}' has been retracted.".format(group.name), 'success')
        return redirect(url_for('GroupsView:index'))

    @route('/<name>/leave', methods=['POST'])
    def leave(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user_id=current_user.id).first()
        if not membership:
            flash("You are not a member of the group '{}'.".format(group.name), 'warning')
            return redirect(url_for('GroupsView:index'))
        if membership.is_applying:
            flash("You have already applied to this group. Please retract your application if you want to leave.", 'warning')
            return redirect(url_for('GroupsView:index'))
        db.session.delete(membership)
        db.session.commit()
        flash("Your membership to the group '{}' has been removed.".format(group.name), 'success')
        return redirect(url_for('GroupsView:index'))

    def admin(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user_id=current_user.id).first()
        if not membership or membership.is_applying:
            flash('You are not a member of this group.', 'error')
            return redirect(url_for('GroupsView:index'))
        group_edit_form = GroupEditForm(obj=group)
        return render_template('groups/admin.html', group=group, group_edit_form=group_edit_form)

    @route('/<name>/admin/accept_application', methods=['POST'])
    def accept_application(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        #if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
        #    abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, is_applying=True).first()
        if not membership:
            abort(404)
        membership.is_applying = False
        membership.accepted_by = current_user
        membership.joined_on = datetime.datetime.utcnow()
        db.session.add(membership)
        db.session.commit()
        flash("The application from '{}' has been accepted.".format(membership.user.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/reject_application', methods=['POST'])
    def reject_application(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        #if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
        #    abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, is_applying=True).first()
        if not membership:
            abort(404)
        # TODO: Maybe send an email ? Allow some text ?
        db.session.delete(membership)
        db.session.commit()
        flash("The application from '{}' has been rejected.".format(membership.user.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/remove_admin', methods=['POST'])
    def remove_admin(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, is_admin=True).first()
        if not membership:
            abort(404)
        membership.is_admin = False
        db.session.add(membership)
        db.session.commit()
        flash('User "{}" was removed admin rights from the group "{}"'.format(membership.user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/make_admin', methods=['POST'])
    def make_admin(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, is_admin=False).first()
        if not membership:
            abort(404)
        membership.is_admin = True
        db.session.add(membership)
        db.session.commit()
        flash('User "{}" was given admin rights from the group "{}"'.format(membership.user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/remove_ping', methods=['POST'])
    def remove_ping(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, can_ping=True).first()
        if not membership:
            abort(404)
        membership.can_ping = False
        db.session.add(membership)
        db.session.commit()
        flash('User "{}" was removed ping rights from the group "{}"'.format(membership.user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/make_ping', methods=['POST'])
    def make_ping(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id, can_ping=False).first()
        if not membership:
            abort(404)
        membership.can_ping = True
        db.session.add(membership)
        db.session.commit()
        flash('User "{}" was given ping rights from the group "{}"'.format(membership.user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/<name>/admin/kick', methods=['POST'])
    def kick(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id).first()
        if not membership:
            abort(404)
        db.session.delete(membership)
        db.session.commit()
        flash('User "{}" was removed from the group "{}"'.format(membership.user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

