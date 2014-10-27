import time
from celery.utils.log import get_task_logger
from newauth.app import create_celery
from newauth.models import db, User
from newauth.eveapi import AuthenticationException

celery = create_celery()
logger = get_task_logger(__name__)


@celery.task(bind=True, default_retry_delay=30 * 60)
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
    # Artifically limit ourselves for CCP. Will need a better solution
    time.sleep(1)
    return user.status
