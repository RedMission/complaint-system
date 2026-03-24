from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('complaints.db')
    cursor = conn.cursor()
    
    # 创建投诉表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        typeText TEXT NOT NULL,
        location TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        demand TEXT,
        contact_name TEXT NOT NULL,
        contact_phone TEXT NOT NULL,
        contact_email TEXT,
        files INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        statusText TEXT DEFAULT '待处理',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')
    
    # 创建处理日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS process_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        status TEXT NOT NULL,
        statusText TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        comment TEXT NOT NULL,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    )''')
    
    conn.commit()
    conn.close()

# 初始化数据库
init_db()

# 健康检查端点
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

# 提交投诉
@app.route('/api/complaints', methods=['POST'])
def submit_complaint():
    try:
        data = request.json
        
        # 提取数据
        complaint_id = data['id']
        complaint_type = data['type']
        type_text = data['typeText']
        location = data['location']
        title = data['title']
        description = data['description']
        demand = data.get('demand', '')
        contact_name = data['contact']['name']
        contact_phone = data['contact']['phone']
        contact_email = data['contact'].get('email', '')
        files = data.get('files', 0)
        status = data.get('status', 'pending')
        status_text = data.get('statusText', '待处理')
        created_at = data['createdAt']
        updated_at = data['updatedAt']
        
        # 保存投诉数据
        conn = sqlite3.connect('complaints.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO complaints 
        (id, type, typeText, location, title, description, demand, contact_name, contact_phone, contact_email, files, status, statusText, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            complaint_id, complaint_type, type_text, location, title, description, demand,
            contact_name, contact_phone, contact_email, files, status, status_text, created_at, updated_at
        ))
        
        # 保存处理日志
        process_logs = data.get('processLogs', [])
        for log in process_logs:
            cursor.execute('''
            INSERT INTO process_logs (complaint_id, status, statusText, timestamp, comment)
            VALUES (?, ?, ?, ?, ?)
            ''', (complaint_id, log['status'], log['statusText'], log['timestamp'], log['comment']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': complaint_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 查询投诉
@app.route('/api/complaints/<id>', methods=['GET'])
def get_complaint(id):
    try:
        conn = sqlite3.connect('complaints.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询投诉信息
        cursor.execute('SELECT * FROM complaints WHERE id = ?', (id,))
        complaint = cursor.fetchone()
        
        if not complaint:
            return jsonify({'success': False, 'error': '投诉不存在'}), 404
        
        # 查询处理日志
        cursor.execute('SELECT * FROM process_logs WHERE complaint_id = ? ORDER BY timestamp', (id,))
        logs = cursor.fetchall()
        
        conn.close()
        
        # 构建响应数据
        complaint_data = {
            'id': complaint['id'],
            'type': complaint['type'],
            'typeText': complaint['typeText'],
            'location': complaint['location'],
            'title': complaint['title'],
            'description': complaint['description'],
            'demand': complaint['demand'],
            'contact': {
                'name': complaint['contact_name'],
                'phone': complaint['contact_phone'],
                'email': complaint['contact_email']
            },
            'files': complaint['files'],
            'status': complaint['status'],
            'statusText': complaint['statusText'],
            'createdAt': complaint['created_at'],
            'updatedAt': complaint['updated_at'],
            'processLogs': [
                {
                    'status': log['status'],
                    'statusText': log['statusText'],
                    'timestamp': log['timestamp'],
                    'comment': log['comment']
                }
                for log in logs
            ]
        }
        
        return jsonify({'success': True, 'data': complaint_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 获取所有投诉（用于后台管理）
@app.route('/api/complaints', methods=['GET'])
def get_all_complaints():
    try:
        conn = sqlite3.connect('complaints.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM complaints ORDER BY created_at DESC')
        complaints = cursor.fetchall()
        
        conn.close()
        
        # 构建响应数据
        complaints_data = []
        for complaint in complaints:
            complaints_data.append({
                'id': complaint['id'],
                'type': complaint['type'],
                'typeText': complaint['typeText'],
                'location': complaint['location'],
                'title': complaint['title'],
                'description': complaint['description'],
                'demand': complaint['demand'],
                'contact': {
                    'name': complaint['contact_name'],
                    'phone': complaint['contact_phone'],
                    'email': complaint['contact_email']
                },
                'files': complaint['files'],
                'status': complaint['status'],
                'statusText': complaint['statusText'],
                'createdAt': complaint['created_at'],
                'updatedAt': complaint['updated_at']
            })
        
        return jsonify({'success': True, 'data': complaints_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 更新投诉状态
@app.route('/api/complaints/<id>', methods=['PUT'])
def update_complaint(id):
    try:
        data = request.json
        
        conn = sqlite3.connect('complaints.db')
        cursor = conn.cursor()
        
        # 更新投诉状态
        if 'status' in data:
            cursor.execute('''
            UPDATE complaints 
            SET status = ?, statusText = ?, updated_at = ?
            WHERE id = ?
            ''', (data['status'], data['statusText'], data['updatedAt'], id))
        
        # 添加处理日志
        if 'processLogs' in data:
            for log in data['processLogs']:
                # 检查日志是否已存在
                cursor.execute('''
                SELECT * FROM process_logs 
                WHERE complaint_id = ? AND timestamp = ?
                ''', (id, log['timestamp']))
                if not cursor.fetchone():
                    cursor.execute('''
                    INSERT INTO process_logs (complaint_id, status, statusText, timestamp, comment)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (id, log['status'], log['statusText'], log['timestamp'], log['comment']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)