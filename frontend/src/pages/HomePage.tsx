import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

const API = 'http://localhost:3000/api';

const CATEGORIES = [
    'TRANG CHỦ', 'CÔNG NGHỆ', 'KINH TẾ', 'THỂ THAO',
    'SỨC KHỎE', 'GIẢI TRÍ', 'GIÁO DỤC', 'DU LỊCH', 'PHÁP LUẬT'
];

interface NewsArticle {
    id: number; title: string; summary: string | null; content: string;
    image_url: string | null; category: string; source: string;
    published_at: string; score?: number;
}
interface Props {
    user: { id: number; username: string; email: string };
    token: string;
    onLogout: () => void;
    theme: 'dark' | 'light';
    onToggleTheme: () => void;
}

function SkeletonCard() {
    return (
        <div className="skel-card">
            <div className="skel-img skeleton" />
            <div className="skel-body">
                <div className="skel-title skeleton" />
                <div className="skel-desc skeleton" />
                <div className="skel-meta skeleton" />
            </div>
        </div>
    );
}

function formatDate(d: string) {
    try {
        return new Date(d).toLocaleDateString('vi-VN', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    } catch { return d; }
}

function getScoreInfo(score: number) {
    if (score >= 0.85) return { label: 'Highly Relevant', cls: 'score-high' };
    if (score >= 0.6) return { label: 'Relevant', cls: 'score-mid' };
    return { label: 'Normal', cls: 'score-low' };
}

export default function HomePage({ user, token, onLogout, theme, onToggleTheme }: Props) {
    const navigate = useNavigate();
    const [latestNews, setLatestNews] = useState<NewsArticle[]>([]);
    const [recommendedNews, setRecommendedNews] = useState<NewsArticle[]>([]);
    const [activeCategory, setActiveCategory] = useState('TRANG CHỦ');
    const [loading, setLoading] = useState(true);
    const [latestCount, setLatestCount] = useState(10);
    const [recCount, setRecCount] = useState(10);

    useEffect(() => { fetchData(); }, [activeCategory]);

    const fetchData = async () => {
        setLoading(true);
        try {
            const latestUrl = activeCategory === 'TRANG CHỦ'
                ? `${API}/news/latest`
                : `${API}/news/category/${encodeURIComponent(activeCategory)}`;
            const [latestRes, recRes] = await Promise.all([
                axios.get(latestUrl),
                axios.get(`${API}/recommend/${user.id}`),
            ]);
            setLatestNews(latestRes.data);
            setRecommendedNews(recRes.data);
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally { setLoading(false); }
    };

    const handleClick = async (article: NewsArticle) => {
        try {
            await axios.post(`${API}/behavior`, {
                user_id: user.id, news_id: article.id, action: 'click',
            });
        } catch { }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        navigate(`/article/${article.id}`);
    };

    return (
        <>
            <header>
                <div className="container header-inner">
                    <div className="logo">
                        <div className="logo-icon">📰</div>
                        <span>New recommendation system</span>
                    </div>
                    <nav>
                        {CATEGORIES.map((cat) => (
                            <button
                                key={cat}
                                className={`nav-link ${activeCategory === cat ? 'active' : ''}`}
                                onClick={() => { 
                                    setActiveCategory(cat); 
                                    setLatestCount(10); 
                                    window.scrollTo({ top: 0, behavior: 'smooth' }); 
                                }}
                            >
                                {cat}
                            </button>
                        ))}
                    </nav>
                    <div className="header-right">
                        <button className="theme-toggle" onClick={onToggleTheme} title="Chuyển giao diện sáng/tối">
                            {theme === 'dark' ? (
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" /></svg>
                            ) : (
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
                            )}
                        </button>
                        <div className="user-badge">
                            <div className="avatar">{user.username[0].toUpperCase()}</div>
                            <span className="user-name">{user.username}</span>
                        </div>
                        <button className="btn btn-danger" onClick={onLogout}>Đăng xuất</button>
                    </div>
                </div>
            </header>

            <main className="container">
                <div className="page-grid">
                    {/* Left Column */}
                    <section>
                        <div className="section-title">
                            <span className="icon" />
                            TIN MỚI
                        </div>
                        <AnimatePresence mode="wait">
                            {loading ? (
                                <div>
                                    {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
                                </div>
                            ) : (
                                <motion.div
                                    key={activeCategory}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.3 }}
                                >
                                    {latestNews.length === 0 ? (
                                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>
                                            Chưa có bài viết nào. Hãy chạy crawler trước.
                                        </p>
                                    ) : latestNews.slice(0, latestCount).map((article) => (
                                        <div
                                            key={article.id} className="news-card"
                                            onClick={() => handleClick(article)}
                                        >
                                            <img
                                                className="card-img"
                                                src={article.image_url || 'https://placehold.co/320x220/1e1e2a/6b6b85?text=No+Image'}
                                                alt={article.title}
                                                onError={(e) => { (e.target as HTMLImageElement).src = 'https://placehold.co/320x220/1e1e2a/6b6b85?text=No+Image'; }}
                                            />
                                            <div className="card-body">
                                                <h3 className="card-title">{article.title}</h3>
                                                {article.summary && <p className="card-desc">{article.summary}</p>}
                                                <div className="card-meta">
                                                    <span className="category-tag">{article.category}</span>
                                                    <span>{article.source}</span>
                                                    <span>•</span>
                                                    <span>{formatDate(article.published_at)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                    {latestNews.length > latestCount && (
                                        <button className="btn-loadmore" onClick={() => setLatestCount(c => c + 10)}>
                                            Xem thêm bài viết →
                                        </button>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </section>

                    {/* Right Column */}
                    <section>
                        <div className="section-title recommend">
                            <span className="icon" />
                            TIN GỢI Ý DÀNH CHO BẠN
                        </div>
                        <AnimatePresence mode="wait">
                            {loading ? (
                                <div>
                                    {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
                                </div>
                            ) : (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.3, delay: 0.1 }}
                                >
                                    {recommendedNews.length === 0 ? (
                                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>
                                            Đọc thêm bài viết để hệ thống gợi ý cho bạn.
                                        </p>
                                    ) : recommendedNews.slice(0, recCount).map((article) => {
                                        const si = article.score ? getScoreInfo(article.score) : null;
                                        return (
                                            <div
                                                key={article.id} className="news-card"
                                                onClick={() => handleClick(article)}
                                            >
                                                <img
                                                    className="card-img"
                                                    src={article.image_url || 'https://placehold.co/320x220/1e1e2a/6b6b85?text=No+Image'}
                                                    alt={article.title}
                                                    onError={(e) => { (e.target as HTMLImageElement).src = 'https://placehold.co/320x220/1e1e2a/6b6b85?text=No+Image'; }}
                                                />
                                                <div className="card-body">
                                                    <h3 className="card-title">{article.title}</h3>
                                                    <div className="card-meta">
                                                        <span className="category-tag">{article.category}</span>
                                                        <span>{formatDate(article.published_at)}</span>
                                                        {si && (
                                                            <span className={`score-badge ${si.cls}`}>
                                                                {article.score!.toFixed(2)} {si.label}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    {recommendedNews.length > recCount && (
                                        <button className="btn-loadmore" onClick={() => setRecCount(c => c + 10)}>
                                            Xem thêm gợi ý →
                                        </button>
                                    )}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </section>
                </div>
            </main>
        </>
    );
}
