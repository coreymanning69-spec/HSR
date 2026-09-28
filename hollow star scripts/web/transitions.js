// Title cards and toasts shown over any screen: floor arrivals, Star awareness
// changes, unlocks. Same visual language as the cutscene frame.

const reduced = () => document.body.classList.contains('reduced-motion')
  || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

let cardQueue = Promise.resolve();

// Full-screen floor/chapter card. Queued so two arrivals never overlap.
export function titleCard(eyebrow, title, {hold = 2600} = {}) {
  cardQueue = cardQueue.then(() => new Promise(resolve => {
    const node = document.createElement('div');
    node.className = 'title-card';
    node.setAttribute('role', 'status');
    node.innerHTML = `<p class="title-card-eyebrow">${esc(eyebrow)}</p><div class="title-card-rule"></div><h2 class="title-card-title">${esc(title)}</h2>`;
    document.body.appendChild(node);
    requestAnimationFrame(() => node.classList.add('is-in'));
    const dismiss = () => { node.classList.remove('is-in'); node.classList.add('is-out'); setTimeout(() => { node.remove(); resolve(); }, reduced() ? 0 : 700); };
    node.addEventListener('click', dismiss, {once: true});
    setTimeout(dismiss, reduced() ? 1200 : hold);
  }));
  return cardQueue;
}

// Small corner notice for unlocks and Star awareness changes.
export function storyToast(text, {ms = 4200} = {}) {
  const node = document.createElement('div');
  node.className = 'story-toast';
  node.setAttribute('role', 'status');
  node.innerHTML = `<span class="story-toast-glyph" aria-hidden="true"></span><span>${esc(text)}</span>`;
  document.body.appendChild(node);
  requestAnimationFrame(() => node.classList.add('is-in'));
  setTimeout(() => { node.classList.remove('is-in'); setTimeout(() => node.remove(), 500); }, ms);
}
