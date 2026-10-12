import { useState } from 'react';
import appShellCss from '../styles/app-shell.css?inline';
import usePageStyle from '../components/usePageStyle.js';
import useToast from '../components/useToast.js';
import TopNav from '../components/TopNav.jsx';

// 사진첩 예시 데이터 (화면 확인용). 서버 연동 때 백엔드 /history 결과로 바꾼다.
// 합성할 때마다 '최근 작업'에 자동으로 쌓이고(saved: false), 마음에 들면 저장해서 '전체'로 옮긴다.
const SAMPLE_ITEMS = [
  { id: 1, img: 'SpringWarm_Female', d: '2026.10.09 11:20', saved: false, fav: false },
  { id: 2, img: 'SummerCool_Female', d: '2026.10.09 11:02', saved: false, fav: false },
  { id: 3, img: 'AutumnWarm_Male', d: '2026.10.08 20:45', saved: false, fav: false },
  { id: 4, img: 'MtFuji_Female', d: '2026.10.08 18:30', saved: false, fav: false },
  { id: 25, img: 'Paris_Female', d: '2026.10.08 15:12', saved: false, fav: false },
  { id: 26, img: 'girl_sitting', d: '2026.10.07 22:40', saved: false, fav: false },
  { id: 5, img: 'girl_Santorini', d: '2026.09.20 14:32', saved: true, fav: true },
  { id: 6, img: 'NewYork_Male', d: '2026.09.20 11:18', saved: true, fav: false },
  { id: 7, img: 'Paris_Female', d: '2026.09.19 21:03', saved: true, fav: true },
  { id: 8, img: 'BaseballCap_Male', d: '2026.09.18 16:27', saved: true, fav: false },
  { id: 9, img: 'girl_sitting', d: '2026.09.17 13:45', saved: true, fav: true },
  { id: 10, img: 'Watch_Female', d: '2026.09.16 09:12', saved: true, fav: false },
  { id: 11, img: 'girl_bag', d: '2026.09.15 18:20', saved: true, fav: false },
  { id: 12, img: 'Watch_Male', d: '2026.09.14 20:11', saved: true, fav: false },
  { id: 13, img: 'RooftopParty_Female', d: '2026.09.13 19:40', saved: true, fav: false },
  { id: 14, img: 'man_watch', d: '2026.09.12 15:05', saved: true, fav: true },
  { id: 15, img: 'girl_hat', d: '2026.09.11 12:30', saved: true, fav: false },
  { id: 16, img: 'Yacht_Female', d: '2026.09.10 17:55', saved: true, fav: false },
  { id: 17, img: 'man_car', d: '2026.09.08 10:22', saved: true, fav: false },
  { id: 18, img: 'Handbag_Female', d: '2026.09.07 21:48', saved: true, fav: true },
  { id: 19, img: 'Supercar_Male', d: '2026.09.05 14:10', saved: true, fav: false },
  { id: 20, img: 'LuxuryCar_Female', d: '2026.09.03 11:36', saved: true, fav: false },
  { id: 21, img: 'PrivateJet_Male', d: '2026.09.01 16:02', saved: true, fav: false },
  { id: 22, img: 'SpringWarm_Female', d: '2026.08.29 13:15', saved: true, fav: false },
  { id: 23, img: 'NewYork_Male', d: '2026.08.27 19:50', saved: true, fav: true },
  { id: 24, img: 'SummerCool_Female', d: '2026.08.25 10:08', saved: true, fav: false },
];

const VIEWS = {
  all: { label: '전체', desc: '상상을 현실로 만든 나만의 작품들을 한눈에 확인해보세요.', match: (it) => it.saved },
  recent: { label: '최근 작업', desc: '합성할 때마다 자동으로 쌓입니다. 마음에 드는 결과만 저장해보세요.', match: (it) => !it.saved },
  fav: { label: '좋아요', desc: '좋아요를 누른 이미지를 모아 볼 수 있습니다.', match: (it) => it.fav },
};

// "2026.09.20 14:32" -> 정렬용 숫자 문자열 / 날짜 부분
const sortKey = (d) => d.replace(/[^0-9]/g, '');
const dayOf = (d) => d.slice(0, 10).replace(/\./g, '-');

export default function MyPage() {
  usePageStyle(appShellCss, 'MOA — 마이페이지');
  const [items, setItems] = useState(SAMPLE_ITEMS);
  const [view, setView] = useState('all');
  const [date, setDate] = useState('');
  const [sort, setSort] = useState('new');
  const [toast, showToast] = useToast();

  const soon = (e) => { e.preventDefault(); showToast('준비 중입니다'); };

  let list = items.filter(VIEWS[view].match);
  if (date) list = list.filter((it) => dayOf(it.d) === date);
  list = [...list].sort((a, b) => (sort === 'new' ? sortKey(b.d).localeCompare(sortKey(a.d)) : sortKey(a.d).localeCompare(sortKey(b.d))));

  const save = (id) => {
    setItems((all) => all.map((it) => (it.id === id ? { ...it, saved: true } : it)));
    showToast('사진첩에 저장했습니다');
  };
  const toggleFav = (id) => setItems((all) => all.map((it) => (it.id === id ? { ...it, fav: !it.fav } : it)));

  return (
    <>
      <TopNav />

      <div className="as-shell">
        <aside className="as-sidebar">
          <div className="as-side-list">
            <a className="as-side-item active" href="/mypage">내 정보</a>
            <a className="as-side-item" href="#album">사진첩</a>
            <a className="as-side-item" href="#" onClick={soon}>설정</a>
            <a className="as-side-item" href="#" onClick={soon}>고객센터</a>
          </div>
        </aside>

        <div className="as-mypage-grid">
          <main>
            <section className="as-panel as-album" id="album">
              <div className="as-album-head">
                <div>
                  <h3>사진첩</h3>
                  <p>{VIEWS[view].desc}</p>
                </div>
                <div className="as-head-tools">
                  <label className="as-date" title="날짜를 선택하면 그날 만든 이미지만 보여줍니다">
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
                    {v.label} <span className="count">{items.filter(v.match).length}</span>
                  </button>
                ))}
              </div>

              <div className="as-grid">
                {list.map((it) => (
                  <div className="as-card" key={it.id}>
                    <div className="as-thumb">
                      <img src={`/assets/gallery/${it.img}.jpg`} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      <button type="button" className={'as-heart' + (it.fav ? ' liked' : '')} onClick={() => toggleFav(it.id)}>{it.fav ? '♥' : '♡'}</button>
                    </div>
                    <div className="as-card-foot">
                      <span>{it.d}</span>
                      {it.saved
                        ? <span className="more">⋯</span>
                        : <button type="button" className="as-save-btn" onClick={() => save(it.id)}>저장</button>}
                    </div>
                  </div>
                ))}
              </div>
              <p className="as-empty" hidden={list.length > 0}>표시할 이미지가 없습니다.</p>
            </section>
          </main>

          <aside className="as-mypage-side">
            <div className="as-panel as-profile-card">
              <div className="as-profile-avatar"><img src="/assets/gallery/girl_sitting.jpg" alt="" /></div>
              <div className="as-profile-name">MOA User</div>
              <div className="as-profile-email">moa.user@example.com</div>
              <p className="as-profile-bio">일상의 모든 것을,<br />새로운 배경으로 만들어보세요.</p>
            </div>

            <div className="as-panel">
              <h3 style={{ fontSize: 15, marginBottom: 8 }}>계정 설정</h3>
              <ul className="as-settings-list">
                {['프로필 수정', '이메일 변경', '비밀번호 변경', '알림 설정'].map((t) => (
                  <li key={t} onClick={soon}>{t} <span>›</span></li>
                ))}
              </ul>
              <button className="as-logout-btn" onClick={soon}>⎋ 로그아웃</button>
            </div>
          </aside>
        </div>
      </div>

      <div className={'toast' + (toast.show ? ' show' : '')}>{toast.msg}</div>
    </>
  );
}
