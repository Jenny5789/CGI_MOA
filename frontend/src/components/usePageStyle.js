import { useLayoutEffect } from 'react';

// 페이지마다 자기 CSS만 켠다. 홈, 합성하기, 마이페이지의 CSS가 body와 공통 색상 값을 서로 다르게 정의해서
// 한꺼번에 켜 두면 충돌하기 때문이다. 페이지를 떠나면 그 CSS를 뺀다.
export default function usePageStyle(cssText, title) {
  useLayoutEffect(() => {
    const el = document.createElement('style');
    el.textContent = cssText;
    document.head.appendChild(el);
    const prevTitle = document.title;
    if (title) document.title = title;
    return () => {
      el.remove();
      document.title = prevTitle;
    };
  }, [cssText, title]);
}
