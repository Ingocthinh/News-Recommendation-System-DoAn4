"""
ML Service Flask API
====================
Cung cấp API cho hệ thống gợi ý tin tức.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from recommender import HybridNewsRecommender
import threading
import sys
import os
import json

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)

recommender = HybridNewsRecommender()
training_status = {"status": "idle", "message": ""}

# Load model on startup hoặc auto-train
print("\n🚀 Đang khởi động ML Service...")
if recommender.load_model():
    training_status = {"status": "ready", "message": "Model loaded successfully"}
    print("✅ Model đã load thành công")
else:
    print("⚠️ Chưa có model. Thử auto-train...")
    try:
        recommender.load_all_data()
        recommender.build_content_model()
        recommender.build_collaborative_model()
        recommender.build_category_model()
        recommender.save_model()
        training_status = {"status": "ready", "message": "Auto-trained on startup"}
        print("✅ Auto-train thành công!")
    except Exception as e:
        training_status = {"status": "no_model", "message": f"No data available: {str(e)}"}
        print(f"❌ Auto-train thất bại: {e}")


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "OK",
        "model_loaded": recommender.news_df is not None,
        "news_count": len(recommender.news_df) if recommender.news_df is not None else 0,
        "training_status": training_status
    })


@app.route('/recommend/<user_id>', methods=['GET'])
def recommend(user_id):
    top_n = request.args.get('top_n', default=10, type=int)
    mode = request.args.get('mode', default='hybrid', type=str)

    if recommender.news_df is None:
        return jsonify({"error": "Model not trained yet"}), 503

    recommendations = recommender.get_recommendations(user_id, top_n=top_n, mode=mode)
    return jsonify(recommendations)


@app.route('/record-action', methods=['POST'])
def record_action():
    data = request.get_json()
    user_id = data.get('user_id')
    news_id = data.get('news_id')
    action = data.get('action')
    dwell_time = data.get('dwell_time', 0)

    if not user_id or not news_id or not action:
        return jsonify({"error": "Missing user_id, news_id or action"}), 400

    recommender.record_interaction(user_id, news_id, action, dwell_time)
    return jsonify({"status": "success", "message": "Interaction recorded"})


@app.route('/train-model', methods=['POST'])
def train():
    global training_status
    if training_status.get("status") == "training":
        return jsonify({"message": "Training already in progress..."})

    def train_worker():
        global training_status
        try:
            training_status = {"status": "training", "message": "Training in progress..."}
            recommender.load_all_data()
            recommender.build_content_model()
            recommender.build_collaborative_model()
            recommender.build_category_model()
            recommender.save_model()
            training_status = {"status": "ready", "message": "Training complete!"}
        except Exception as e:
            training_status = {"status": "error", "message": str(e)}

    thread = threading.Thread(target=train_worker)
    thread.start()
    return jsonify({"message": "Training started in background..."})


@app.route('/retrain', methods=['POST'])
def retrain():
    """Retrain nhanh: reload data và build lại models"""
    global training_status
    if training_status.get("status") == "training":
        return jsonify({"message": "Training already in progress..."})

    def retrain_worker():
        global training_status
        try:
            training_status = {"status": "training", "message": "Retraining..."}
            recommender.load_all_data()
            recommender.build_content_model()
            recommender.build_collaborative_model()
            recommender.build_category_model()
            recommender.save_model()
            training_status = {"status": "ready", "message": "Retrain complete!"}
        except Exception as e:
            training_status = {"status": "error", "message": str(e)}

    thread = threading.Thread(target=retrain_worker)
    thread.start()
    return jsonify({"message": "Retrain started..."})


@app.route('/status', methods=['GET'])
def status():
    model_dir = os.path.join(os.path.dirname(__file__), "model")
    info = {"training_status": training_status}

    report_path = os.path.join(model_dir, "evaluation_report.json")
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            info["evaluation_report"] = json.load(f)

    return jsonify(info)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
