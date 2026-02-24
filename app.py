from flask import Flask, Response, render_template, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import os
import cv2
import base64

from rtmp_camera_stream import RtmpCameraStream
from admin_init import init_admin
from config import Config
from db_model import db, save_sensor_data, SoilSensorData

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化admin
    init_admin(app)

    # 初始化数据库
    db.init_app(app)

    # 创建全局CameraStream对象
    camera = RtmpCameraStream(app.config['RTMP_URL'], app.config['IMAGE_FOLDER'])

    @app.route('/camera/stream')
    def camera_stream():
        return Response(camera.stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/sensor', methods=['POST'])
    def sensor():
        try:
            # 获取JSON数据
            data = request.get_json()
            
            # 检查必需字段是否存在
            if not data or not all(key in data for key in ['d1', 'd2', 'd3', 'd4']):
                return jsonify({'error': 'Missing required parameters: d1, d2, d3, d4'}), 400
            
            # 提取数据
            d1 = data['d1']
            d2 = data['d2']
            d3 = data['d3']
            d4 = data['d4']
            
            # 在这里处理传感器数据（示例：打印到控制台）
            print(f'Received sensor data: 湿度={d1}, 温度={d2}, 电导率={d3}, pH={d4}')
            
            # 可以添加您的业务逻辑，如存储到数据库、转发到其他服务等
            save_sensor_data(d1,d2,d3,d4)
            # 返回成功响应
            return jsonify({
                'status': 'success',
                'message': 'Sensor data received successfully',
                'data': {
                    'd1': d1,
                    'd2': d2,
                    'd3': d3,
                    'd4': d4
                }
            }), 200
            
        except Exception as e:
            # 处理异常情况
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
            
    @app.route('/admin/sensordata/json')
    def sensor_data_json():
        # 获取查询参数
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        # 解析日期参数
        if start_str and end_str:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        else:
            # 默认返回最近24小时的数据
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=24)
        
        # 查询数据库
        sensor_data = SoilSensorData.query.filter(
            SoilSensorData.timestamp >= start_date,
            SoilSensorData.timestamp <= end_date
        ).order_by(SoilSensorData.timestamp.asc()).all()
        
        # 转换为JSON格式
        data = []
        for item in sensor_data:
            data.append({
                'timestamp': item.timestamp.isoformat(),
                'moisture': item.moisture,
                'temperature': item.temperature,
                'conductivity': item.conductivity,
                'ph': item.ph
            })
        
        return jsonify(data)
        
    @app.route('/image_folder/<filename>')
    def image_preview(filename):
        return render_template('/admin/ImagePreview.html', filename=filename)
    
    @app.route('/image_base64/<filename>', methods=['GET'])
    def get_image_base64_upload(filename):
        uploads = app.config['IMAGE_FOLDER']
        file_path = os.path.join(uploads, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        # 读取图片并编码为base64
        img = cv2.imread(file_path)
        if img is None:
            return jsonify({'error': '无法读取图片'}), 400

        _, buffer = cv2.imencode('.png', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return jsonify({'image_data': img_base64})
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)