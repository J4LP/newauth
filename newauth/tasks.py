import os
import time
from celery.utils.log import get_task_logger
from newauth.models import db, User, celery, AuthContact
from newauth.eveapi import AuthenticationException


logger = get_task_logger(__name__)


@celery.task(bind=True, default_retry_delay=30 * 60, rate_limit='1/s')
def update_user(self, user_id):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        raise Exception('User {} not found'.format(user_id))
    try:
        logger.info('Updating user {}'.format(user_id))
        user.update_keys()
        user.update_status()
    except AuthenticationException as e:
        # Bad user is bad
        raise e
    except Exception as e:
        # API Error ?
        logger.warn('API error encountered, retrying later: ' + str(e))
        self.retry(exc=e)
    db.session.add(user)
    db.session.commit()
    return user.status


@celery.task
def update_contacts():
    AuthContact.update_contacts()


@celery.task
def update_users():
    user_ids = [a[0] for a in db.session.query(User.user_id).all()]
    for user_id in user_ids:
        update_user.apply_async(args=[user_id], queue='newauth')
