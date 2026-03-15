import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';

const API = 'http://localhost:3000/api';

interface Article {
    id: number; title: string; content: string; summary: string | null;
    image_url: string | null; category: string; source: string;
    published_at: string; url: string;
}
interface Props {
    user: { id: number; username: string };
    token: string;
    onLogout: () => void;
    theme: 'dark' | 'light';
    onToggleTheme: () => void;
}

export default function ArticlePage({ user, onLogout, theme, onToggleTheme }: Props) {
    const { id } = useParams();
    const navigate = useNavigate();
    const [article, setArticle] = useState<Article | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchArticle = async () => {
            setLoading(true);
            try {
                const res = await axios.get(`${API}/news/${id}`);
                setArticle(res.data);
                await axios.post(`${API}/behavior`, {
                    user_id: user.id, news_id: Number(id), action: 'read',
                });
            } catch (err) {
                console.error('Failed to load article:', err);
            } finally { setLoading(false); }
        };
        fetchArticle();
    }, [id]);

    const headerBar = (
        <header>
            <div className="container header-inner">
                <div className="logo" onClick={() => navigate('/')}>
                    <div className="logo-icon">📰</div>
                    <span>New recommendation system</span>
                </div>
                <nav>
                    {['TRANG CHỦ', 'CÔNG NGHỆ', 'KINH TẾ', 'THỂ THAO', 'SỨC KHỎE', 'GIẢI TRÍ', 'GIÁO DỤC', 'DU LỊCH', 'PHÁP LUẬT'].map(cat => (
                        <button key={cat} className="nav-link" onClick={() => navigate('/')}>
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
    );

    if (loading) {
        return (
            <>
                {headerBar}
                <div className="article-page">
                    <div className="skeleton" style={{ height: 40, width: '80%', marginBottom: 16 }} />
                    <div className="skeleton" style={{ height: 20, width: '40%', marginBottom: 32 }} />
                    <div className="skeleton" style={{ height: 350, width: '100%', marginBottom: 32 }} />
                    <div className="skeleton" style={{ height: 16, width: '100%', marginBottom: 8 }} />
                    <div className="skeleton" style={{ height: 16, width: '100%', marginBottom: 8 }} />
                    <div className="skeleton" style={{ height: 16, width: '90%', marginBottom: 8 }} />
                </div>
            </>
        );
    }

    if (!article) {
        return (
            <>
                {headerBar}
                <div className="article-page" style={{ textAlign: 'center', paddingTop: 80 }}>
                    <h2>Không tìm thấy bài viết</h2>
                    <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 20 }}>
                        Về trang chủ
                    </button>
                </div>
            </>
        );
    }

    const paragraphs = article.content.split('\n').filter(p => p.trim().length > 0);

    return (
        <>
            {headerBar}

            <motion.div
                className="article-page"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <button className="btn-back" onClick={() => navigate(-1)}>
                    <span className="btn-back-icon">←</span>
                    <span>Quay lại</span>
                </button>

                <div className="article-header">
                    <h1>{article.title}</h1>
                    <div className="article-header-meta">
                        <span className="category-tag">{article.category}</span>
                        <span>{article.source}</span>
                        <span>•</span>
                        <span>{new Date(article.published_at).toLocaleDateString('vi-VN', {
                            day: '2-digit', month: 'long', year: 'numeric',
                            hour: '2-digit', minute: '2-digit'
                        })}</span>
                        <a href={article.url} target="_blank" rel="noopener noreferrer" className="btn-source">
                            🔗 Đọc bài gốc
                        </a>
                    </div>
                </div>

                {article.image_url && (
                    <img
                        className="article-hero-img"
                        src={article.image_url}
                        alt={article.title}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                )}

                <div className="article-content">
                    {paragraphs.map((p, i) => (
                        <p key={i}>{p}</p>
                    ))}
                </div>
            </motion.div>
        </>
    );
}
