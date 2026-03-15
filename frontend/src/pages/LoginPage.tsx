import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';

const API = 'http://localhost:3000/api';

interface Props {
    onLogin: (user: any, token: string) => void;
}

export default function LoginPage({ onLogin }: Props) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const res = await axios.post(`${API}/auth/login`, { email, password });
            onLogin(res.data.user, res.data.token);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Đăng nhập thất bại');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <motion.div
                className="auth-card"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <div style={{ textAlign: 'center', marginBottom: 8 }}>
                    <div className="logo" style={{ justifyContent: 'center', marginBottom: 16 }}>
                        <div className="logo-icon">📰</div>
                        <span>NewsAI</span>
                    </div>
                </div>
                <h1>Đăng Nhập</h1>
                <p className="subtitle">Chào mừng trở lại! Đăng nhập để xem tin gợi ý.</p>

                {error && <div className="auth-error">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Email</label>
                        <input
                            type="email" placeholder="you@example.com"
                            value={email} onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Mật khẩu</label>
                        <input
                            type="password" placeholder="••••••••"
                            value={password} onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button type="submit" className="btn-auth" disabled={loading}>
                        {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
                    </button>
                </form>

                <div className="auth-switch">
                    Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link>
                </div>
            </motion.div>
        </div>
    );
}
