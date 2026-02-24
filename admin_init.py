from flask_admin import Admin
from flask_admin.base import BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin

from db_model import db, SoilSensorData

class HomeView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/HomeView.html')

class CameraView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/CameraView.html')
    
class VideoReplayView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/VideoReplayView.html')

class SensorView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/SensorView.html')
    
class SoilSensorDataVisualizationView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/SoilSensorDataVisualizationView.html')

def init_admin(app):
    admin = Admin(
        app,
        name='农作物图像采集系统',
        # template_mode='bootstrap3',
        index_view=HomeView(name='首页', endpoint='HomeView', url='/')
    )
    admin.add_view(CameraView(name='视频监控页面', endpoint='CameraView'))
    # admin.add_view(VideoReplayView(name='视频回放页面', endpoint='VideoReplayView'))
    admin.add_view(
        FileAdmin(
            app.config['IMAGE_FOLDER'],
            '/image_folder/',
            name='存储图片',
            endpoint='/image_folder/'
        )
    )
    # admin.add_view(SensorView(name='传感器数据', endpoint='SensorView'))
    # 添加数据库表视图
    admin.add_view(ModelView(SoilSensorData, db.session, name='土壤传感器数据',endpoint='SoilSensorData'))
    admin.add_view(SoilSensorDataVisualizationView(name='土壤传感器数据可视化', endpoint='SoilSensorDataVisualizationView'))
    return admin