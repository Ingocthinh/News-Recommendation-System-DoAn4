"""
Hybrid News Recommendation System
===================================
Kết hợp 3 phương pháp:
1. Content-Based Filtering: TF-IDF với tối ưu cho tiếng Việt
2. Collaborative Filtering: Sparse SVD (Matrix Factorization)
3. Category Profiling: Xây dựng profile sở thích theo chuyên mục

Tập trung vào bài viết trong DB (không phụ thuộc CSV training data).
Gợi ý chính xác dựa trên lịch sử tương tác thực tế của người dùng.
"""

import pandas as pd
import numpy as np
import os
import sys
import gc
import json
import joblib
import time
import sqlite3
import warnings
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize, LabelEncoder
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

warnings.filterwarnings('ignore')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# Constants
# ============================================================
ACTION_WEIGHTS = {
    'share': 10.0,
    'like': 8.0,
    'click': 5.0,
    'read': 5.0,
    'view': 2.0,
}

# Hybrid Weights
CONTENT_WEIGHT = 0.45
COLLAB_WEIGHT = 0.20
CATEGORY_WEIGHT = 0.20
RECENCY_WEIGHT = 0.15

SVD_K = 50
MAX_TFIDF_FEATURES = 50000
TFIDF_NGRAM = (1, 2)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DATA_TRAIN_DIR = os.path.join(BASE_DIR, "..", "data_train")
MODEL_DIR = os.path.join(BASE_DIR, "model")
DB_PATH = os.path.join(DATA_DIR, "news.db")


class HybridNewsRecommender:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.news_df = None
        self.behaviors_df = None
        self.users_df = None

        # Components
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.user_factors = None
        self.news_factors = None
        self.user_means = None
        self.collab_user_to_idx = None
        self.collab_news_to_idx = None
        self.category_map = None
        self.news_id_to_idx = None
        self.news_id_to_category = None
        self.popular_news = []
        self._news_categories_series = None

    def load_all_data(self):
        """Load dữ liệu từ Database SQLite (nguồn dữ liệu chính)"""
        print("\n[1/3] Đang tải dữ liệu...")

        # 1. Load News từ DB
        if not os.path.exists(DB_PATH):
            raise ValueError(f"Database không tồn tại: {DB_PATH}")

        conn = sqlite3.connect(DB_PATH)

        # Load news articles
        db_news = pd.read_sql_query(
            "SELECT id, title, content, summary, category, source, url, published_at FROM News",
            conn
        )

        if len(db_news) == 0:
            conn.close()
            raise ValueError("Không có bài viết nào trong DB! Chạy crawler trước.")

        db_news['news_id'] = db_news['id']
        db_news['text_combined'] = (
            db_news['title'].fillna('') + ' ' +
            db_news['summary'].fillna('') + ' ' +
            db_news['content'].fillna('')
        )
        db_news['published_at'] = pd.to_datetime(db_news['published_at'], errors='coerce').fillna(pd.Timestamp.now())

        self.news_df = db_news[['news_id', 'title', 'text_combined', 'category', 'published_at']].copy()
        self.news_df = self.news_df.drop_duplicates('news_id')
        self.news_df = self.news_df.dropna(subset=['text_combined'])

        self.news_id_to_idx = {nid: i for i, nid in enumerate(self.news_df['news_id'])}
        self.news_id_to_category = dict(zip(self.news_df['news_id'], self.news_df['category']))
        self._news_categories_series = self.news_df['category'].values

        print(f"  -> {len(self.news_df)} bài viết đã tải từ DB")

        # 2. Load Behaviors từ DB
        try:
            db_bhv = pd.read_sql_query(
                "SELECT user_id, news_id, action, dwell_time, timestamp FROM Behavior",
                conn
            )
            if len(db_bhv) > 0:
                db_bhv['user_id'] = db_bhv['user_id'].astype(str)
                db_bhv['news_id'] = db_bhv['news_id'].astype(int)
                # Chuyển timestamp từ DateTime sang Unix timestamp
                db_bhv['timestamp'] = pd.to_datetime(db_bhv['timestamp'], errors='coerce')
                db_bhv['timestamp'] = db_bhv['timestamp'].apply(
                    lambda x: x.timestamp() if pd.notna(x) else time.time()
                )
                db_bhv['rating'] = db_bhv['action'].map(ACTION_WEIGHTS).fillna(1.0)
                if 'dwell_time' in db_bhv.columns:
                    db_bhv['rating'] += np.log1p(db_bhv['dwell_time'].fillna(0))
                self.behaviors_df = db_bhv
                print(f"  -> {len(db_bhv)} behaviors đã tải từ DB")
            else:
                self.behaviors_df = None
                print("  -> Chưa có behaviors trong DB")
        except Exception as e:
            self.behaviors_df = None
            print(f"  -> Không tải được behaviors: {e}")

        conn.close()

        # 3. Tính Global Popularity
        if self.behaviors_df is not None and len(self.behaviors_df) > 0:
            popular = self.behaviors_df.groupby('news_id')['rating'].sum().sort_values(ascending=False)
            self.popular_news = popular.index.tolist()
        else:
            # Nếu chưa có behaviors, dùng bài mới nhất làm popular
            self.popular_news = self.news_df.sort_values('published_at', ascending=False)['news_id'].tolist()

        print(f"  -> Top popular: {len(self.popular_news)} bài")

    def build_content_model(self):
        """Xây dựng TF-IDF content model"""
        print("\n[2/3] Đang xây dựng Content-Based Model...")

        max_features = min(MAX_TFIDF_FEATURES, len(self.news_df) * 20)

        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=TFIDF_NGRAM,
            sublinear_tf=True,
            min_df=1,
            max_df=0.95
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.news_df['text_combined'])
        print(f"  -> TF-IDF Matrix: {self.tfidf_matrix.shape}")

    def build_collaborative_model(self):
        """Xây dựng Collaborative Filtering bằng SVD"""
        print("\n[3/3] Đang xây dựng Collaborative Model...")

        if self.behaviors_df is None or len(self.behaviors_df) == 0:
            print("  -> Bỏ qua (chưa có behaviors)")
            self.user_factors = None
            self.news_factors = None
            return

        bhv = self.behaviors_df.copy()
        # Chỉ giữ behaviors cho news có trong DB
        bhv = bhv[bhv['news_id'].isin(self.news_id_to_idx)]

        if len(bhv) < 5:
            print(f"  -> Bỏ qua (chỉ có {len(bhv)} behaviors hợp lệ)")
            self.user_factors = None
            self.news_factors = None
            return

        bhv_agg = bhv.groupby(['user_id', 'news_id'])['rating'].sum().reset_index()

        u_enc = LabelEncoder()
        n_enc = LabelEncoder()
        bhv_agg['u_idx'] = u_enc.fit_transform(bhv_agg['user_id'].astype(str))
        bhv_agg['n_idx'] = n_enc.fit_transform(bhv_agg['news_id'].astype(str))

        n_users = bhv_agg['u_idx'].nunique()
        n_news = bhv_agg['n_idx'].nunique()

        interactions = csr_matrix(
            (bhv_agg['rating'], (bhv_agg['u_idx'], bhv_agg['n_idx'])),
            shape=(n_users, n_news)
        )

        # SVD
        k = min(SVD_K, min(n_users, n_news) - 1)
        if k < 2:
            print(f"  -> Bỏ qua SVD (k={k} quá nhỏ)")
            self.user_factors = None
            self.news_factors = None
            return

        U, sigma, Vt = svds(interactions.astype(float), k=k)

        self.user_factors = U @ np.diag(sigma)
        self.news_factors = Vt.T
        self.user_means = np.array(interactions.mean(axis=1)).flatten()

        self.collab_user_to_idx = dict(zip(u_enc.classes_, range(len(u_enc.classes_))))
        self.collab_news_to_idx = dict(zip(n_enc.classes_, range(len(n_enc.classes_))))
        print(f"  -> CF Factors: users={n_users}, news={n_news}, k={k}")

    def build_category_model(self):
        """Xây dựng profile sở thích chuyên mục cho từng user"""
        print("Đang xây dựng Category Profiles...")
        self.category_map = defaultdict(lambda: defaultdict(float))

        if self.behaviors_df is not None and len(self.behaviors_df) > 0:
            for _, row in self.behaviors_df.iterrows():
                uid = str(row['user_id'])
                nid = row['news_id']
                rating = row['rating']
                cat = self.news_id_to_category.get(nid)
                if cat:
                    self.category_map[uid][cat] += rating

        self.category_map = {k: dict(v) for k, v in self.category_map.items()}
        print(f"  -> {len(self.category_map)} user profiles")

    def _normalize(self, scores):
        """Chuẩn hóa scores về [0, 1]"""
        if scores is None or len(scores) == 0:
            return np.zeros(len(self.news_df))
        mn, mx = scores.min(), scores.max()
        if mx > mn:
            return (scores - mn) / (mx - mn)
        return np.zeros_like(scores)

    def get_content_scores(self, user_id):
        """Tính content-based scores dựa trên lịch sử đọc"""
        if self.behaviors_df is None or len(self.behaviors_df) == 0:
            return np.zeros(len(self.news_df))

        user_bhv = self.behaviors_df[self.behaviors_df['user_id'] == user_id].copy()
        if user_bhv.empty:
            return np.zeros(len(self.news_df))

        now = time.time()

        # Time decay: bài đọc gần đây ảnh hưởng nhiều hơn
        user_bhv = user_bhv.copy()
        user_bhv['timestamp'] = pd.to_numeric(user_bhv['timestamp'], errors='coerce').fillna(now)
        age_hours = (now - user_bhv['timestamp'].values) / 3600.0
        age_array = np.asarray(age_hours, dtype=np.float64)
        # Decay: halve weight every 24 hours
        user_bhv['decay_weight'] = np.exp(-0.03 * np.clip(age_array, 0, 10000))

        user_bhv['final_weight'] = user_bhv['rating'] * user_bhv['decay_weight']

        # Xây dựng user profile vector
        weighted_vectors = []
        total_weight = 0.0
        for _, row in user_bhv.iterrows():
            try:
                nid = int(row['news_id'])
                if nid in self.news_id_to_idx:
                    idx = self.news_id_to_idx[nid]
                    w = float(row['final_weight'])
                    weighted_vectors.append(self.tfidf_matrix[idx] * w)
                    total_weight += w
            except:
                continue

        if not weighted_vectors:
            return np.zeros(len(self.news_df))

        user_profile = sum(weighted_vectors) / (total_weight + 1e-9)
        scores = self.tfidf_matrix.dot(user_profile.T).toarray().flatten()
        return scores

    def get_collab_scores(self, user_id):
        """Tính collaborative filtering scores"""
        if self.user_factors is None:
            return None
        if user_id not in self.collab_user_to_idx:
            return None

        u_idx = self.collab_user_to_idx[user_id]
        preds = self.user_factors[u_idx] @ self.news_factors.T + self.user_means[u_idx]

        full_scores = np.zeros(len(self.news_df))
        for nid_str, col_idx in self.collab_news_to_idx.items():
            try:
                nid = int(nid_str)
            except:
                nid = nid_str
            if nid in self.news_id_to_idx:
                full_scores[self.news_id_to_idx[nid]] = preds[col_idx]
        return full_scores

    def get_category_scores(self, user_id):
        """Tính category preference scores"""
        if user_id not in self.category_map:
            return np.zeros(len(self.news_df))

        prefs = self.category_map[user_id]
        total = sum(prefs.values())
        if total == 0:
            return np.zeros(len(self.news_df))

        norm_prefs = {k: v / total for k, v in prefs.items()}
        scores = np.array([norm_prefs.get(cat, 0.0) for cat in self._news_categories_series])
        return scores

    def get_recency_scores(self):
        """Tính recency scores (bài mới điểm cao hơn)"""
        now = pd.Timestamp.now()
        diff_days = (now - self.news_df['published_at']).dt.total_seconds() / (24 * 3600)
        # Exponential decay: halve score every 3 days
        scores = np.exp(-0.23 * diff_days.values.clip(0))
        return scores

    def get_recommendations(self, user_id, top_n=10, mode='hybrid'):
        """Tạo gợi ý cho user"""
        user_id = str(user_id)

        # Lấy danh sách bài đã đọc
        interacted = set()
        if self.behaviors_df is not None and len(self.behaviors_df) > 0:
            try:
                user_bhv = self.behaviors_df[self.behaviors_df['user_id'] == user_id]
                if not user_bhv.empty:
                    # Chuyển đổi an toàn, bỏ qua các giá trị không hợp lệ
                    valid_ids = []
                    for val in user_bhv['news_id']:
                        try:
                            if isinstance(val, (list, np.ndarray)):
                                valid_ids.append(int(val[0]))
                            else:
                                valid_ids.append(int(val))
                        except (ValueError, TypeError):
                            continue
                    interacted = set(valid_ids)
            except Exception as e:
                print(f"  ⚠️ Lỗi lấy danh sách bài đã đọc: {e}")
                import traceback
                traceback.print_exc()

        # Kiểm tra user có lịch sử không
        has_history = len(interacted) > 0

        # Tính scores
        try:
            c_scores = self.get_content_scores(user_id)
        except Exception as e:
            print(f"  ⚠️ Lỗi get_content_scores: {e}")
            c_scores = np.zeros(len(self.news_df))
        
        try:
            cf_scores = self.get_collab_scores(user_id)
        except Exception as e:
            print(f"  ⚠️ Lỗi get_collab_scores: {e}")
            cf_scores = None
        cat_scores = self.get_category_scores(user_id)
        recency_scores = self.get_recency_scores()

        # Kết hợp scores
        if mode == 'content':
            final_scores = c_scores.copy()
        elif mode == 'collaborative':
            final_scores = cf_scores.copy() if cf_scores is not None else np.zeros(len(self.news_df))
        elif mode == 'popularity':
            final_scores = np.zeros(len(self.news_df))
            for i, nid in enumerate(self.popular_news[:100]):
                if nid in self.news_id_to_idx:
                    final_scores[self.news_id_to_idx[nid]] = 100 - i
        else:  # Hybrid
            c_norm = self._normalize(c_scores)
            cat_norm = self._normalize(cat_scores)
            r_norm = self._normalize(recency_scores)

            if has_history:
                if cf_scores is not None:
                    cf_norm = self._normalize(cf_scores)
                    final_scores = (
                        CONTENT_WEIGHT * c_norm +
                        COLLAB_WEIGHT * cf_norm +
                        CATEGORY_WEIGHT * cat_norm +
                        RECENCY_WEIGHT * r_norm
                    )
                else:
                    # Có lịch sử nhưng chưa có CF model
                    final_scores = (
                        0.50 * c_norm +
                        0.25 * cat_norm +
                        0.25 * r_norm
                    )
            else:
                # Cold start: user mới, ưu tiên bài mới + diverse categories
                final_scores = 0.3 * r_norm

                # Thêm diversity bonus
                categories = self.news_df['category'].values
                unique_cats = list(set(categories))
                cat_bonus = np.zeros(len(self.news_df))
                for cat in unique_cats:
                    cat_mask = categories == cat
                    # Cho mỗi category, ưu tiên bài mới nhất
                    cat_indices = np.where(cat_mask)[0]
                    if len(cat_indices) > 0:
                        cat_recency = recency_scores[cat_indices]
                        top_in_cat = cat_indices[np.argsort(cat_recency)[::-1][:3]]
                        for rank, idx in enumerate(top_in_cat):
                            cat_bonus[idx] = 0.7 - rank * 0.1
                final_scores += cat_bonus

        # Loại bỏ bài đã đọc
        for nid in interacted:
            if nid in self.news_id_to_idx:
                final_scores[self.news_id_to_idx[nid]] = -1

        # Chọn top candidates
        candidate_indices = np.where(final_scores >= 0)[0]
        if len(candidate_indices) == 0:
            return []

        sorted_candidates = candidate_indices[np.argsort(final_scores[candidate_indices])[::-1]]

        # Diversity: giảm penalty cho category trùng
        results = []
        seen_categories = defaultdict(int)

        for idx in sorted_candidates[:min(100, len(sorted_candidates))]:
            if len(results) >= top_n:
                break

            news_row = self.news_df.iloc[idx]
            cat = news_row['category']

            raw_score = final_scores[idx]
            # Penalty giảm dần cho category trùng
            penalty = 0.10 * seen_categories[cat]
            adjusted_score = max(0, raw_score - penalty)

            results.append({
                "news_id": int(news_row['news_id']),
                "title": news_row['title'],
                "category": cat,
                "raw_score": raw_score,
                "adjusted_score": adjusted_score,
            })
            seen_categories[cat] += 1

        # Sắp xếp theo adjusted_score
        results.sort(key=lambda x: x['adjusted_score'], reverse=True)
        results = results[:top_n]

        # Scale scores cho UI (0.5 - 0.99)
        max_s = results[0]['adjusted_score'] if results else 1.0
        final_results = []
        for item in results:
            if max_s > 0:
                scaled = 0.50 + (item['adjusted_score'] / (max_s + 1e-9)) * 0.49
            else:
                scaled = 0.50
            final_results.append({
                "news_id": item['news_id'],
                "title": item['title'],
                "category": item['category'],
                "score": round(min(scaled, 0.99), 4)
            })

        # Fallback: nếu không có kết quả, trả về bài phổ biến/mới nhất
        if not final_results:
            for nid in self.popular_news[:top_n]:
                if nid in self.news_id_to_idx:
                    idx = self.news_id_to_idx[nid]
                    final_results.append({
                        "news_id": int(nid),
                        "title": self.news_df.iloc[idx]['title'],
                        "category": self.news_df.iloc[idx]['category'],
                        "score": 0.5
                    })

        return final_results

    def record_interaction(self, user_id, news_id, action, dwell_time=0):
        """Ghi nhận tương tác real-time"""
        user_id = str(user_id)
        try:
            if isinstance(news_id, (list, np.ndarray)) and len(news_id) > 0:
                news_id = int(news_id[0])
            else:
                news_id = int(news_id)
        except:
            pass

        rating = ACTION_WEIGHTS.get(action, 1.0)
        if dwell_time and dwell_time > 0:
            rating += np.log1p(dwell_time)

        # 1. Cập nhật behaviors_df
        new_row = pd.DataFrame([{
            'user_id': user_id,
            'news_id': news_id,
            'action': action,
            'dwell_time': dwell_time or 0,
            'rating': rating,
            'timestamp': float(time.time())
        }])

        if self.behaviors_df is not None:
            self.behaviors_df = pd.concat([self.behaviors_df, new_row], ignore_index=True)
        else:
            self.behaviors_df = new_row

        # 2. Cập nhật category_map
        cat = self.news_id_to_category.get(news_id)
        if cat:
            if self.category_map is None:
                self.category_map = {}
            if user_id not in self.category_map:
                self.category_map[user_id] = {}
            # Boost mạnh cho real-time interaction
            self.category_map[user_id][cat] = self.category_map[user_id].get(cat, 0.0) + (rating * 15.0)

        print(f"  Recorded: User {user_id} -> News {news_id} ({action}) [Category: {cat}]")
        return True

    def save_model(self):
        """Lưu model"""
        print("\nĐang lưu model...")
        os.makedirs(MODEL_DIR, exist_ok=True)

        joblib.dump(self.news_df, os.path.join(MODEL_DIR, "news_df.pkl"))
        joblib.dump(self.tfidf_vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
        joblib.dump(self.tfidf_matrix, os.path.join(MODEL_DIR, "tfidf_matrix.pkl"))
        joblib.dump(self.news_id_to_idx, os.path.join(MODEL_DIR, "news_id_to_idx.pkl"))
        joblib.dump(self.news_id_to_category, os.path.join(MODEL_DIR, "news_id_to_category.pkl"))
        joblib.dump(self.category_map or {}, os.path.join(MODEL_DIR, "category_map.pkl"))
        joblib.dump(self.behaviors_df, os.path.join(MODEL_DIR, "behaviors_df.pkl"))
        joblib.dump(self.popular_news, os.path.join(MODEL_DIR, "popular_news.pkl"))

        collab_data = {
            'user_factors': self.user_factors,
            'news_factors': self.news_factors,
            'user_means': self.user_means,
            'collab_user_to_idx': self.collab_user_to_idx,
            'collab_news_to_idx': self.collab_news_to_idx
        }
        joblib.dump(collab_data, os.path.join(MODEL_DIR, "collab_model.pkl"))

        print(f"  -> Model đã lưu tại {MODEL_DIR}")

    def load_model(self):
        """Load model đã train"""
        try:
            self.news_df = joblib.load(os.path.join(MODEL_DIR, "news_df.pkl"))
            self.tfidf_vectorizer = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
            self.tfidf_matrix = joblib.load(os.path.join(MODEL_DIR, "tfidf_matrix.pkl"))
            self.news_id_to_idx = joblib.load(os.path.join(MODEL_DIR, "news_id_to_idx.pkl"))
            self.news_id_to_category = joblib.load(os.path.join(MODEL_DIR, "news_id_to_category.pkl"))
            self.category_map = joblib.load(os.path.join(MODEL_DIR, "category_map.pkl"))
            self.behaviors_df = joblib.load(os.path.join(MODEL_DIR, "behaviors_df.pkl"))
            self.popular_news = joblib.load(os.path.join(MODEL_DIR, "popular_news.pkl"))
            self._news_categories_series = self.news_df['category'].values

            c = joblib.load(os.path.join(MODEL_DIR, "collab_model.pkl"))
            self.user_factors = c.get('user_factors')
            self.news_factors = c.get('news_factors')
            self.user_means = c.get('user_means')
            self.collab_user_to_idx = c.get('collab_user_to_idx')
            self.collab_news_to_idx = c.get('collab_news_to_idx')

            print(f"  -> Model loaded: {len(self.news_df)} bài viết")
            return True
        except Exception as e:
            print(f"  -> Không load được model: {e}")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("  TRAINING HYBRID NEWS RECOMMENDER")
    print("=" * 60)
    recommender = HybridNewsRecommender()
    recommender.load_all_data()
    recommender.build_content_model()
    recommender.build_collaborative_model()
    recommender.build_category_model()
    recommender.save_model()
    print("\n✅ Training hoàn tất!")
