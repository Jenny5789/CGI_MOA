import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext.jsx';
import Home from './pages/Home.jsx';
import Studio from './pages/Studio.jsx';
import MyPage from './pages/MyPage.jsx';

// 합성하기 화면은 로그인해야 들어갈 수 있다. 로그인하지 않았으면 홈으로 보내고 로그인 팝업을 띄운다.
function RequireLogin({ children }) {
  const { loggedIn } = useAuth();
  if (!loggedIn) return <Navigate to="/" replace state={{ needLogin: true }} />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/studio" element={<RequireLogin><Studio /></RequireLogin>} />
        <Route path="/mypage" element={<MyPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
