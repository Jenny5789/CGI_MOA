import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import appShellCss from '../styles/app-shell.css?inline';
import usePageStyle from '../components/usePageStyle.js';
import useToast from '../components/useToast.js';
import TopNav from '../components/TopNav.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import { listResults, updateResult } from '../api/results.js';
import { formatKoreanDate } from '../utils/date.js';
import { AccountPanel, ServiceSettings } from '../mypage/Settings.jsx';
import Support from '../mypage/Support.jsx';
import { PhotoMenu, PhotoViewer } from '../mypage/PhotoTools.jsx';
import { downloadResult } from '../utils/download.js';

// 주소 뒤 # 표시로 가운데 화면을 고른다
// - 없음·#account-profile|email|password: 내 정보. 상자 상단 탭으로 항목 선택, 기본 프로필 수정
// - #album: 사진첩, #settings: 설정 (알림, 합성 기본 설정), #support: 고객센터
const ACCOUNT_ITEMS = [['profile', '프로필 수정'], ['email', '이메일 변경'], ['password', '비밀번호 변경']];
const readHash = (hash) => {
  const account = ACCOUNT_ITEMS.find(([key]) => hash === `#account-${key}`);
  if (account) return { view: 'info', item: account[0] };
  if (hash === '#album') return { view: 'album' };
  if (hash === '#settings') return { view: 'settings' };
  if (hash === '#support') return { view: 'support' };
  return { view: 'info', item: 'profile' };
};

// 사진첩은 서버의 결과 목록(명세 6-1)을 보여 준다. 탭, 날짜, 정렬을 바꿀 때마다 서버에 다시 묻는다.
// 사진첩에는 저장한 결과만 나온다. 저장하지 않은 결과는 합성하기 화면의 '내 작업 기록'에서 보고 저장할 수 있다 (24시간 뒤 삭제).
// filters: 서버에 보낼 조건, count: 탭 옆 숫자로 쓸 counts 항목
const VIEWS = {
  all: { label: '전체', desc: '상상을 현실로 만든 나만의 작품을 한눈에 확인할 수 있습니다.', filters: { saved: true }, count: 'saved' },
  fav: { label: '좋아요', desc: '좋아요를 누른 이미지를 모아 볼 수 있습니다.', filters: { saved: true, favorite: true }, count: 'favorite' },
};

export default function MyPage() {
  usePageStyle(appShellCss, 'MOA — 마이페이지');
  const { loggedIn, me, setMe } = useAuth();
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [status, setStatus] = useState('loading'); // loading / ready / error
  const [errorMsg, setErrorMsg] = useState('');
  const [reload, setReload] = useState(0); // 저장/좋아요 뒤 목록을 다시 받을 때 올린다
  const [pending, setPending] = useState(() => new Set()); // 서버 응답을 기다리는 결과 (버튼 두 번 누름 방지)
  const [view, setView] = useState('all');
  const [date, setDate] = useState('');
  const [sort, setSort] = useState('new');
  const [toast, showToast] = useToast(2400);
  const [viewing, setViewing] = useState(null); // 크게 보기 중인 결과
  const { hash } = useLocation();
  const page = readHash(hash);

  // 메뉴를 고르면 맨 위부터 보이게
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [page.view, page.item]);

  const download = async (it) => {
    try {
      await downloadResult(it);
    } catch (e) {
      showToast(e.message);
    }
  };

  useEffect(() => {
    if (!loggedIn) return undefined;
    let ignore = false; // 탭을 빨리 바꿔서 앞 요청의 응답이 늦게 와도 덮어쓰지 않게
    setStatus('loading');
    listResults({ ...VIEWS[view].filters, date, sort })
      .then((data) => {
        if (ignore) return;
        setItems(data.items);
        setCounts(data.counts);
        setStatus('ready');
      })
      .catch((e) => {
        if (ignore) return;
        setErrorMsg(e.message);
        setStatus('error');
      });
    return () => { ignore = true; };
  }, [loggedIn, view, date, sort, reload]);

  const patch = async (id, change, doneMsg) => {
    if (pending.has(id)) return;
    setPending((s) => new Set(s).add(id));
    try {
      await updateResult(id, change);
      if (doneMsg) showToast(doneMsg);
    } catch (e) {
      showToast(e.message);
    } finally {
      setPending((s) => { const n = new Set(s); n.delete(id); return n; });
      setReload((n) => n + 1);
    }
  };

  const save = (id) => patch(id, { saved: true }, '사진첩에 저장했습니다.');
  const toggleFav = (id) => {
    const it = items.find((x) => x.result_id === id);
    if (!it || pending.has(id)) return;
    // 하트는 바로 바뀌어 보이게 하고, 서버 응답 뒤 목록을 다시 받아 맞춘다
    setItems((all) => all.map((x) => (x.result_id === id ? { ...x, favorite: !x.favorite } : x)));
    patch(id, { favorite: !it.favorite });
  };

  const list = loggedIn ? items : [];
  let emptyMsg = '';
  if (!loggedIn) emptyMsg = '로그인하면 사진첩을 볼 수 있습니다.';
  else if (status === 'error') emptyMsg = errorMsg;
  else if (status === 'loading' && !items.length) emptyMsg = '불러오는 중입니다.';
  else if (status === 'ready' && !items.length) emptyMsg = '표시할 이미지가 없습니다.';

  return (
    <>
      <TopNav />

      <div className="as-shell">
        <aside className="as-sidebar">
          <div className="as-side-list">
            <a className={'as-side-item' + (page.view === 'info' ? ' active' : '')} href="#">내 정보</a>
            <a className={'as-side-item' + (page.view === 'album' ? ' active' : '')} href="#album">사진첩</a>
            <a className={'as-side-item' + (page.view === 'settings' ? ' active' : '')} href="#settings">설정</a>
            <a className={'as-side-item' + (page.view === 'support' ? ' active' : '')} href="#support">고객센터</a>
          </div>
        </aside>

        <main className="as-mypage-main">
            {/* 내 정보: 상자 하나에 프로필과 계정 설정 탭 */}
            {page.view === 'info' && (loggedIn
              ? <AccountPanel items={ACCOUNT_ITEMS} item={page.item} me={me} onMe={setMe} showToast={showToast} />
              : <p className="as-empty">로그인하면 내 정보를 확인할 수 있습니다.</p>)}
            {page.view === 'settings' && <ServiceSettings showToast={showToast} />}
            {page.view === 'support' && <Support />}
            <section className="as-panel as-album" id="album" hidden={page.view !== 'album'}>
              <div className="as-album-head">
                <div>
                  <h3>사진첩</h3>
                  <p>{VIEWS[view].desc}</p>
                </div>
                <div className="as-head-tools">
                  <label className="as-date" title="날짜를 선택하면 그날 만든 이미지만 표시합니다.">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="1" /><line x1="3" y1="10" x2="21" y2="10" /><line x1="8" y1="3" x2="8" y2="7" /><line x1="16" y1="3" x2="16" y2="7" /></svg>
                    <input type="date" aria-label="날짜 선택" value={date} onChange={(e) => setDate(e.target.value)} />
                  </label>
                  <button type="button" className="as-date-clear" hidden={!date} onClick={() => setDate('')}>전체 날짜</button>
                  <select className="as-select as-sort" aria-label="정렬" value={sort} onChange={(e) => setSort(e.target.value)}>
                    <option value="new">최신순</option>
                    <option value="old">오래된순</option>
                  </select>
                </div>
              </div>

              <div className="as-tabs">
                {Object.entries(VIEWS).map(([key, v]) => (
                  <button key={key} type="button" className={'as-tab' + (view === key ? ' active' : '')} onClick={() => setView(key)}>
                    {v.label} <span className="count">{loggedIn && counts[v.count] !== undefined ? counts[v.count] : ''}</span>
                  </button>
                ))}
              </div>

              <div className="as-grid">
                {list.map((it) => (
                  <div className="as-card" key={it.result_id}>
                    <div className="as-thumb">
                      <img className="as-thumb-img" src={it.thumb_url} alt="" onClick={() => setViewing(it)} />
                      <button type="button" className={'as-heart' + (it.favorite ? ' liked' : '')} onClick={() => toggleFav(it.result_id)}>{it.favorite ? '♥' : '♡'}</button>
                    </div>
                    <div className="as-card-foot">
                      <span>{formatKoreanDate(it.created_at)}</span>
                      {it.saved
                        ? <PhotoMenu item={it} onView={setViewing} onDownload={download} />
                        : <button type="button" className="as-save-btn" disabled={pending.has(it.result_id)} onClick={() => save(it.result_id)}>저장</button>}
                    </div>
                  </div>
                ))}
              </div>
              <p className="as-empty" hidden={!emptyMsg}>{emptyMsg}</p>
            </section>
        </main>
      </div>

      {viewing && <PhotoViewer item={viewing} onClose={() => setViewing(null)} onDownload={download} />}
      <div className={'toast' + (toast.show ? ' show' : '')}>{toast.msg}</div>
    </>
  );
}
