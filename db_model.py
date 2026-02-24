from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

# 创建db实例但不初始化
db = SQLAlchemy()

def get_china_time():
    return datetime.now(pytz.timezone('Asia/Shanghai'))

class SoilSensorData(db.Model):
    __tablename__ = 'soil_sensor_data'
    
    id = db.Column(db.Integer, primary_key=True)
    moisture = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    conductivity = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_china_time)
    
    def __repr__(self):
        return f'<SoilSensorData {self.id}: M={self.moisture}%, T={self.temperature}°C, EC={self.conductivity}, pH={self.ph}>'

# 保存传感器数据的函数
def save_sensor_data(moisture, temperature, conductivity, ph):
    try:
        sensor_data = SoilSensorData(
            moisture=moisture,
            temperature=temperature,
            conductivity=conductivity,
            ph=ph
        )
        db.session.add(sensor_data)
        db.session.commit()
        return sensor_data
    except Exception as e:
        db.session.rollback()
        print(f"保存数据时出错: {e}")
        return None

# 获取最近N条传感器数据的函数
def get_recent_sensor_data(limit=10):
    return SoilSensorData.query.order_by(SoilSensorData.timestamp.desc()).limit(limit).all()