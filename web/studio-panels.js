/* 합성하기 화면: 양쪽 패널(진행 상황, 내 작업 기록) 접기 / 펼치기
   - 기본값: 양쪽 모두 펼침. 줄이고 싶을 때 사용자가 직접 접는다
   - 사용자가 직접 바꾼 상태는 이 브라우저에 기억한다 */
(() => {
  const shell = document.getElementById('sg-shell');
  if (!shell) return;

  const KEYS = { left: 'moa_panel_left', right: 'moa_panel_right' };
  const read = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const write = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* 저장 불가 시 무시 */ }  };

  const user = { left: read(KEYS.left), right: read(KEYS.right) };
  const fallback = {
    left: () => 'open',
    right: () => 'open',
  };

  function apply() {
    ['left', 'right'].forEach((side) => {
      const v = user[side] === 'open' || user[side] === 'closed' ? user[side] : fallback[side]();
      shell.dataset[side] = v;
      const btn = shell.querySelector('[data-toggle="' + side + '"]');
      if (!btn) return;
      const text = btn.dataset.label + (v === 'open' ? ' 접기' : ' 열기');
      btn.setAttribute('aria-expanded', String(v === 'open'));
      btn.setAttribute('aria-label', text);
      btn.title = text;
    });
  }

  // 폭이 바뀐 뒤 가운데 캔버스가 칸에 다시 맞도록 창 크기 변경 신호를 보낸다 (studio-guide.js 가 이 신호에 맞춰 다시 그린다)
  function refit() {
    setTimeout(() => window.dispatchEvent(new Event('resize')), 300);
  }

  shell.querySelectorAll('[data-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const side = btn.dataset.toggle;
      const next = shell.dataset[side] === 'open' ? 'closed' : 'open';
      user[side] = next;
      write(KEYS[side], next);
      apply();
      refit();
    });
  });

  apply();
})();
