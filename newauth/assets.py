from flask.ext.assets import Bundle, Environment

assets_env = Environment()

common_css = Bundle(
    '../static/less/*.less',
    filters='less',
    output='../public/css/common.css'
)
assets_env.register('common_css', common_css)

common_js = Bundle(
    '../static/bower_components/jquery/dist/jquery.js',
    '../static/bower_components/bootstrap/dist/js/bootstrap.js',
    output='../public/js/common.js'
)
assets_env.register('common_js', common_js)

application_js = Bundle(
    '../static/coffee/*.coffee',
    filters='coffeescript',
    output='../public/js/application.js'
)
assets_env.register('application_js', application_js)
