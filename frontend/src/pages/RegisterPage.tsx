import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';

const API = 'http://localhost:3000/api';

interface Props {
    onLogin: (user: any, token: string) => void;
}

export default function RegisterPage({ onLogin }: Props) {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (password.length < 6) {
            setError('Mật khẩu phải có ít nhất 6 ký tự');
            return;
        }
        setLoading(true);
        try {
            const res = await axios.post(`${API}/auth/register`, { username, email, password });
            onLogin(res.data.user, res.data.token);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Đăng ký thất bại');
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
                <h1>Tạo Tài Khoản</h1>
                <p className="subtitle">Đăng ký để nhận tin tức gợi ý cá nhân hóa.</p>

                {error && <div className="auth-error">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Tên người dùng</label>
                        <input
                            type="text" placeholder="nhap ten dang nhap"
                            value={username} onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
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
                            type="password" placeholder="Ít nhất 6 ký tự"
                            value={password} onChange={(e) => setPassword(e.target.value)}
                            required minLength={6}
                        />
                    </div>
                    <button type="submit" className="btn-auth" disabled={loading}>
                        {loading ? 'Đang tạo tài khoản...' : 'Đăng ký'}
                    </button>
                </form>

                <div className="auth-switch">
                    Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
                </div>
            </motion.div>
        </div>
    );
}
