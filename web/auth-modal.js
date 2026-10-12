/* 로그인 팝업 (시연용). 아이디 test / 비밀번호 test 로만 로그인된다.
   홈, 마이페이지는 로그인 없이 볼 수 있고, 합성하기 화면(studio2.html)으로 들어가려 할 때 로그인을 요구한다.
   로그인 상태는 이 브라우저에만 저장되며 실제 계정 기능(DB)은 없다. */
(() => {
  const KEY = 'moa_logged_in';
  const DEMO_ID = 'test';
  const DEMO_PW = 'test';
  const HOME = 'index-light.html';
  const GATED_PAGE = 'studio2.html'; // 로그인해야 들어갈 수 있는 화면

  const isLoggedIn = () => { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; } };
  const setLoggedIn = (on) => {
    try { if (on) localStorage.setItem(KEY, '1'); else localStorage.removeItem(KEY); } catch (e) { /* 저장 불가 시 무시 */ }
  };

  const page = location.pathname.split('/').pop();

  // 주소창으로 합성하기 화면에 바로 들어와도 로그인하지 않았으면 홈으로 돌려보내 로그인을 유도한다
  if (page === GATED_PAGE && !isLoggedIn()) {
    location.replace(HOME + '#login');
    return;
  }

  const html = `
    <div class="auth-modal-box" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <button type="button" class="auth-modal-close" aria-label="닫기">×</button>
      <h2 class="auth-modal-title" id="auth-modal-title">로그인</h2>
      <p class="auth-modal-sub">MOA에 오신 것을 환영합니다.</p>
      <form id="auth-form" novalidate>
        <label class="auth-field"><span>아이디</span><input type="text" id="auth-id" placeholder="아이디를 입력하세요" autocomplete="username"></label>
        <label class="auth-field"><span>비밀번호</span><input type="password" id="auth-pw" placeholder="비밀번호를 입력하세요" autocomplete="current-password"></label>
        <button type="submit" class="auth-submit">로그인</button>
      </form>
      <p class="auth-modal-foot">아직 계정이 없으신가요? <a data-auth-signup>회원가입</a></p>
    </div>`;

  const modal = document.createElement('div');
  modal.className = 'auth-modal';
  modal.id = 'auth-modal';
  modal.innerHTML = html;

  const toastEl = document.createElement('div');
  toastEl.className = 'auth-toast';

  let toastTimer = null;
  let pendingHref = null; // 로그인 직후 이동할 곳

  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2000);
  }

  function setSub(msg) {
    modal.querySelector('.auth-modal-sub').textContent = msg;
  }

  function open() {
    modal.classList.add('open');
    const first = modal.querySelector('input');
    if (first) setTimeout(() => first.focus(), 0);
  }

  function close() {
    modal.classList.remove('open');
    pendingHref = null;
    setSub('MOA에 오신 것을 환영합니다.');
  }

  function refreshButtons() {
    const on = isLoggedIn();
    document.querySelectorAll('[data-auth="login"]').forEach((el) => { el.textContent = on ? '로그아웃' : '로그인'; });
    document.querySelectorAll('[data-auth="signup"]').forEach((el) => { el.style.display = on ? 'none' : ''; });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(modal);
    document.body.appendChild(toastEl);
    refreshButtons();

    document.querySelectorAll('[data-auth="login"]').forEach((el) => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        if (isLoggedIn()) {
          setLoggedIn(false);
          if (page === GATED_PAGE) { location.replace(HOME); return; }
          refreshButtons();
          toast('로그아웃되었습니다');
        } else {
          open();
        }
      });
    });

    document.querySelectorAll('[data-auth="signup"]').forEach((el) => {
      el.addEventListener('click', (e) => { e.preventDefault(); toast('회원가입은 준비 중입니다'); });
    });

    // 로그인하지 않고 합성하기 화면으로 가는 링크(지금, 합성해보기, 메뉴의 합성하기)를 누르면 막고 로그인 팝업을 띄운다
    document.addEventListener('click', (e) => {
      const a = e.target.closest && e.target.closest('a[href]');
      if (!a || isLoggedIn()) return;
      if (a.getAttribute('href') === GATED_PAGE) {
        e.preventDefault();
        pendingHref = GATED_PAGE;
        setSub('합성하려면 로그인이 필요합니다.');
        open();
      }
    }, true);

    modal.querySelector('.auth-modal-close').addEventListener('click', close);
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });

    modal.querySelector('#auth-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const id = modal.querySelector('#auth-id').value.trim();
      const pw = modal.querySelector('#auth-pw').value;
      if (id === DEMO_ID && pw === DEMO_PW) {
        setLoggedIn(true);
        const go = pendingHref;
        modal.classList.remove('open');
        modal.querySelector('#auth-pw').value = '';
        setSub('MOA에 오신 것을 환영합니다.');
        pendingHref = null;
        refreshButtons();
        if (go) { location.href = go; return; }
        toast('로그인되었습니다');
      } else {
        toast('아이디 또는 비밀번호가 올바르지 않습니다');
      }
    });

    modal.querySelector('[data-auth-signup]').addEventListener('click', () => {
      toast('회원가입은 준비 중입니다');
    });

    // 합성하기 화면에서 튕겨 왔을 때 로그인 팝업을 바로 연다
    if (location.hash === '#login' && !isLoggedIn()) {
      pendingHref = GATED_PAGE;
      setSub('합성하려면 로그인이 필요합니다.');
      open();
    }
  });
})();
