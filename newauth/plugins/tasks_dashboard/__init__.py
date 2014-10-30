from pkg_resources import resource_string
from flask import current_app, render_template_string, flash
from flask.ext.classy import FlaskView, route
from flask.ext.login import login_required
import requests
from newauth.utils import is_admin


class TasksDasboard(object):
    """Small tasks dashboard powered by Celery and Flower"""

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        self.TasksView.register(app)

        # Registering to navbar
        app.navbar['admin'].append(('fa-tasks', 'Tasks', 'TasksView:index'))

        self.app.logger.debug("Tasks Dashboard is enabled.")

    class TasksView(FlaskView):

        decorators = [login_required, is_admin]

        route_base = '/admin/tasks'

        templates = {
            'index': resource_string(__name__, 'templates/index.html'),
            'get': resource_string(__name__, 'templates/get.html')
        }

        def index(self):
            req = requests.get(current_app.config['CELERY_FLOWER_URL'] + 'api/tasks')
            try:
                decoded_json = req.json()
                celery_tasks = [task for task in decoded_json.itervalues()]
            except Exception:
                flash('We could not contact the Flower API at {}'.format(current_app.config['CELERY_FLOWER_URL']))
                celery_tasks = []
            return render_template_string(self.templates['index'], tasks=celery_tasks)

        @route('<task_id>')
        def get(self, task_id):
            req = requests.get(current_app.config['CELERY_FLOWER_URL'] + 'api/task/info/' + task_id)
            try:
                task = req.json()
            except Exception:
                flash('We could not contact the Flower API at {}'.format(current_app.config['CELERY_FLOWER_URL']))
                task = {}
            return render_template_string(self.templates['get'], task=task)

