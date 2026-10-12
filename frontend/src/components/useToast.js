import { useCallback, useEffect, useRef, useState } from 'react';

// 화면 아래에 잠깐 떴다 사라지는 안내 문구
export default function useToast(duration = 1800) {
  const [toast, setToast] = useState({ msg: '', show: false });
  const timer = useRef(null);

  const showToast = useCallback((msg) => {
    setToast({ msg, show: true });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setToast((t) => ({ ...t, show: false })), duration);
  }, [duration]);

  useEffect(() => () => clearTimeout(timer.current), []);

  return [toast, showToast];
}
