"""
Training & Evaluation Script for Hybrid News Recommender
=========================================================
Train model trên dữ liệu DB, đánh giá với các metrics:
- Hit Rate@K
- Precision@K
- Recall@K
- NDCG@K
"""

import sys
import os
import json
import time
import numpy as np
import pandas as pd
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
sys.path.insert(0, BASE_DIR)
from recommender import HybridNewsRecommender


def dcg_at_k(relevances, k):
    """Compute DCG@K"""
    relevances = np.array(relevances[:k])
    if len(relevances) == 0:
        return 0.0
    return np.sum(relevances / np.log2(np.arange(2, len(relevances) + 2)))


def ndcg_at_k(relevances, k):
    """Compute NDCG@K"""
    actual_dcg = dcg_at_k(relevances, k)
    ideal_dcg = dcg_at_k(sorted(relevances, reverse=True), k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_recommender(recommender, test_behaviors, k_values=[5, 10]):
    """Đánh giá model trên tập test"""
    modes = ['popularity', 'content', 'hybrid']

    print("\n" + "=" * 60)
    print("  ĐÁNH GIÁ MODEL")
    print("=" * 60)

    # Nhóm test behaviors theo user
    test_by_user = defaultdict(set)
    for _, row in test_behaviors.iterrows():
        nid = int(row['news_id'])
        if nid in recommender.news_id_to_idx:
            test_by_user[str(row['user_id'])].add(nid)

    valid_users = [u for u, items in test_by_user.items() if len(items) > 0]

    if not valid_users:
        print("  ⚠️ Không có user nào có test behaviors hợp lệ!")
        return {}

    max_eval = min(200, len(valid_users))
    if max_eval < len(valid_users):
        eval_users = list(np.random.choice(valid_users, size=max_eval, replace=False))
    else:
        eval_users = valid_users

    print(f"  Đánh giá trên {len(eval_users)} users, {len(test_behaviors)} test behaviors")

    # Thêm collaborative nếu có
    if recommender.user_factors is not None:
        modes.append('collaborative')

    all_results = {}

    for mode in modes:
        print(f"\n  Mode: {mode.upper()}...")
        results = {k: {'precision': [], 'recall': [], 'ndcg': [], 'hits': 0} for k in k_values}

        for user_id in eval_users:
            held_out = test_by_user[user_id]
            if not held_out:
                continue

            try:
                recs = recommender.get_recommendations(user_id, top_n=max(k_values), mode=mode)
                rec_ids = [r['news_id'] for r in recs]
            except Exception as e:
                continue

            for k in k_values:
                top_k = rec_ids[:k]
                hits = len(set(top_k) & held_out)

                results[k]['precision'].append(hits / k if k > 0 else 0)
                results[k]['recall'].append(hits / len(held_out) if held_out else 0)
                rel = [1.0 if nid in held_out else 0.0 for nid in top_k]
                results[k]['ndcg'].append(ndcg_at_k(rel, k))
                if hits > 0:
                    results[k]['hits'] += 1

        mode_metrics = {}
        for k in k_values:
            n = len(results[k]['precision']) if results[k]['precision'] else 1
            mode_metrics[f'P@{k}'] = round(np.mean(results[k]['precision']) if results[k]['precision'] else 0, 6)
            mode_metrics[f'R@{k}'] = round(np.mean(results[k]['recall']) if results[k]['recall'] else 0, 6)
            mode_metrics[f'NDCG@{k}'] = round(np.mean(results[k]['ndcg']) if results[k]['ndcg'] else 0, 6)
            mode_metrics[f'HR@{k}'] = round(results[k]['hits'] / len(eval_users) if len(eval_users) > 0 else 0, 6)

        all_results[mode] = mode_metrics

    # In bảng so sánh
    print("\n" + "=" * 80)
    print(f"{'Mode':<15} | {'P@5':<8} | {'P@10':<8} | {'NDCG@10':<10} | {'HR@10':<8}")
    print("-" * 80)
    for mode, m in all_results.items():
        print(f"{mode:<15} | {m.get('P@5', 0):<8.4f} | {m.get('P@10', 0):<8.4f} | {m.get('NDCG@10', 0):<10.6f} | {m.get('HR@10', 0):<8.4f}")
    print("=" * 80)

    return all_results


def main():
    print("=" * 60)
    print("  BẮT ĐẦU TRAINING MODEL GỢI Ý TIN TỨC")
    print("=" * 60)

    recommender = HybridNewsRecommender()
    recommender.load_all_data()

    # Nếu có behaviors, split train/test
    if recommender.behaviors_df is not None and len(recommender.behaviors_df) >= 10:
        print("\n📊 Splitting data 80/20 per user...")
        bhv = recommender.behaviors_df.copy()

        # Sắp xếp theo timestamp
        bhv = bhv.sort_values('timestamp')
        
        train_list = []
        test_list = []
        
        for user_id, user_data in bhv.groupby('user_id'):
            if len(user_data) < 3:
                # Nếu user có quá ít tương tác, đưa hết vào train để không mất dữ liệu
                train_list.append(user_data)
                continue
            
            # Chia 80/20 cho từng user
            split_idx = int(len(user_data) * 0.8)
            train_list.append(user_data.iloc[:split_idx])
            test_list.append(user_data.iloc[split_idx:])
            
        train_bhv = pd.concat(train_list) if train_list else pd.DataFrame(columns=bhv.columns)
        test_bhv = pd.concat(test_list) if test_list else pd.DataFrame(columns=bhv.columns)
        
        print(f"  -> Train: {len(train_bhv)}, Test: {len(test_bhv)}")

        # Train trên training set
        recommender.behaviors_df = train_bhv
        recommender.popular_news = train_bhv.groupby('news_id')['rating'].sum().sort_values(ascending=False).index.tolist()
    else:
        test_bhv = None
        print("\n⚠️ Chưa có đủ behaviors để đánh giá (cần ít nhất 10)")

    # Build models
    recommender.build_content_model()
    recommender.build_collaborative_model()
    recommender.build_category_model()

    # Đánh giá nếu có test data
    metrics = {}
    if test_bhv is not None and len(test_bhv) > 0:
        metrics = evaluate_recommender(recommender, test_bhv)
    else:
        print("\n📝 Bỏ qua đánh giá (chưa có test data)")
        metrics = {
            "info": "Chưa có đủ behaviors để đánh giá. Hãy sử dụng hệ thống để tạo dữ liệu tương tác.",
            "content": {"P@5": 0, "P@10": 0, "NDCG@5": 0, "NDCG@10": 0, "HR@5": 0, "HR@10": 0},
            "hybrid": {"P@5": 0, "P@10": 0, "NDCG@5": 0, "NDCG@10": 0, "HR@5": 0, "HR@10": 0},
        }

    # Lưu evaluation report
    os.makedirs(MODEL_DIR, exist_ok=True)
    report_path = os.path.join(MODEL_DIR, "evaluation_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\n📄 Report đã lưu: {report_path}")

    # Train final model trên toàn bộ data
    if test_bhv is not None:
        print("\n🔄 Training final production model (toàn bộ data)...")
        # Reload full behaviors
        recommender2 = HybridNewsRecommender()
        recommender2.load_all_data()
        recommender2.build_content_model()
        recommender2.build_collaborative_model()
        recommender2.build_category_model()
        recommender2.save_model()
    else:
        recommender.save_model()

    print("\n✅ Training hoàn tất!")


if __name__ == "__main__":
    main()
