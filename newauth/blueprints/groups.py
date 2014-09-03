import datetime
from flask import render_template, abort, request, jsonify, redirect, url_for, flash, current_app
from flask.ext.classy import FlaskView, route
from flask.ext.login import current_user, login_required
from newauth.forms import GroupCreateForm, GroupEditForm, GroupApplicationForm
from newauth.models import User, Group, GroupMembership, GroupInvite, db
from newauth.models.enums import GroupType, GroupInviteStatus
from newauth.utils import flash_errors, is_admin


class GroupsView(FlaskView):

    decorators = [login_required]

    def index(self):
        filter = request.args.get('filter')
        if filter == 'member':
            groups = Group.query.filter(Group.members.any(user_id=current_user.id)).all()
        if filter == 'pending':
            groups = Group.query.filter((Group.members.any(user_id=current_user.id, is_applying=True)) | (Group.invites.any(recipient_id=current_user.id))).all()
        if not filter or filter == 'all':
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
        if not membership and not current_user.is_admin():
            flash('You are not a member of this group.', 'danger')
            return redirect(url_for('GroupsView:index'))
        group_edit_form = GroupEditForm(obj=group)
        group_edit_form.type.choices = [(element.name, element.value) for element in list(GroupType)]
        if group_edit_form.is_submitted():
            if group_edit_form.validate():
                if current_user.is_admin_of(group):
                    group_edit_form.populate_obj(group)
                    group.set_type(GroupType[group_edit_form.type.data])
                    db.session.add(group)
                    db.session.commit()
                    flash('Group updated.', 'success')
            else:
                flash_errors(group_edit_form)
            return redirect(url_for('GroupsView:get', name=group.name))
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


    @route('/join/<name>', methods=['GET'])
    def admin_join(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not current_user.is_admin():
            abort(403)
        if group.members.filter_by(user_id=current_user.id).first():
            abort(400)
        membership = GroupMembership(user=current_user, group=group)
        membership.joined_on = datetime.datetime.utcnow()
        db.session.add(membership)
        db.session.commit()
        flash("You have joined the group '{}'".format(group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('/invitation', methods=['POST'])
    def decide_invitation(self):
        group_id = request.form.get('group_id')
        if not group_id:
            abort(400)
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            abort(404)
        membership = group.members.filter_by(user=current_user).first()
        if membership:
            abort(400)
        invitation = group.invites.filter_by(recipient=current_user).first()
        if not invitation or invitation.get_status() != GroupInviteStatus.pending:
            abort(400)
        choice = request.form.get('choice')
        if choice not in ('yes', 'no'):
            abort(400)
        if choice == 'yes':
            membership = GroupMembership(
                group=group,
                user=current_user,
                joined_on=datetime.datetime.utcnow()
            )
            db.session.add(membership)
            db.session.delete(invitation)
            db.session.commit()
            flash("You have joined the group '{}'".format(group.name), 'success')
        if choice == 'no':
            db.session.delete(invitation)
            db.session.commit()
            flash("You have declined the invitation to join the group '{}'".format(group.name), 'info')
        return redirect(url_for('GroupsView:index'))

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

    @route('/<name>/admin/accept_application', methods=['POST'])
    def accept_application(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
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
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        membership = group.members.filter_by(user_id=user_id).first()
        if not membership:
            abort(404)
        user = membership.user.name
        db.session.delete(membership)
        db.session.commit()
        flash('User "{}" was removed from the group "{}"'.format(user, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('<name>/admin/invite', methods=['POST'])
    def invite(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
        user_id = request.form.get('user_id')
        if not user_id:
            abort(400)
        user = User.query.get(user_id)
        if not user:
            abort(404)
        membership = group.members.filter_by(user_id=user_id).first()
        #if membership:
        #    flash('User "{}" has already a membership with the group "{}"'.format(user.name, group.name))
        invite = GroupInvite(
            group=group,
            sender=current_user,
            recipient=user
        )
        db.session.add(invite)
        db.session.commit()
        GroupInvite.new_invite.send(current_app._get_current_object(), invite=invite)
        flash('User "{}" was invited to the group "{}"'.format(user.name, group.name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('<name>/admin/cancel_invite', methods=['POST'])
    def cancel_invite(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
        invite_id = request.form.get('invite_id')
        if not invite_id:
            abort(400)
        invite = group.invites.filter_by(id=invite_id).first()
        if not invite:
            abort(404)
        name = invite.recipient.name
        db.session.delete(invite)
        db.session.commit()
        flash("The invitation to '{}' was cancelled.".format(name), 'success')
        return redirect(url_for('GroupsView:get', name=group.name))

    @route('<name>/admin/search_users')
    def search_users(self, name):
        group = Group.query.filter_by(name=name).first()
        if not group:
            abort(404)
        if not group.members.filter_by(user_id=current_user.id, is_admin=True).first() or not current_user.is_admin():
            abort(403)
        name = request.args.get('name')
        if not name or len(name) < 3:
            abort(400)
        users = User.query.with_entities(User.id, User.name).filter(User.name.ilike('%' + name + '%')).all()[:10]
        return jsonify(results=[{'id': u[0], 'name': u[1]} for u in users])

