# API para exponer el rumbo de la brújula QMC5883L
from qmc5883l import QMC5883L
from flask import Flask, jsonify
import threading

app = Flask(__name__)
brujula = QMC5883L()

@app.route('/api/brujula')
def api_brujula():
    try:
        azimuth = brujula.get_azimuth()
        return jsonify({'ok': True, 'azimuth': azimuth})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

def run_brujula_api():
    app.run(host='0.0.0.0', port=5055, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_brujula_api()
