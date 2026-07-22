// Vanilla JS + Bootstrap 5
(function () {
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  const containerId = "applyModalContainer";
  function ensureContainer() {
    let el = document.getElementById(containerId);
    if (!el) {
      el = document.createElement("div");
      el.id = containerId;
      document.body.appendChild(el);
    }
    return el;
  }

  async function openApplyModal(btn) {
    const isAuth = btn.dataset.auth === "1";
    const loginUrl = btn.dataset.login;
    const kind = btn.dataset.type; // "job" | "intern"
    const id = btn.dataset.id;
    const nextUrl = btn.dataset.next || window.location.pathname + window.location.search;

    if (!isAuth) {
      const reason = kind === "job" ? "job" : "internship";
      window.location.href = `${loginUrl}?next=${encodeURIComponent(nextUrl)}&reason=${reason}`;
      return;
    }

    const url = `/applications/apply/preview/?type=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}&next=${encodeURIComponent(nextUrl)}`;
    const html = await fetch(url, { credentials: "same-origin" }).then(r => r.text());

    const host = ensureContainer();
    host.innerHTML = html;

    const modalEl = document.getElementById("applyModal");
    const modal = new bootstrap.Modal(modalEl);
    modal.show();

    // handle submit via AJAX for a smoother UX
    const form = modalEl.querySelector("#applyForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(form);
        const resp = await fetch(form.action, {
          method: "POST",
          body: fd,
          headers: { "X-CSRFToken": getCookie("csrftoken") }
        }).then(r => r.json());
        if (resp.ok && resp.redirect) {
          modal.hide();
          window.location.href = resp.redirect;
        } else {
          // show small inline error
          alert(resp.error || "Something went wrong. Please try again.");
        }
      });
    }
  }

  // attach to all buttons with .js-apply-btn
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".js-apply-btn");
    if (btn) {
      e.preventDefault();
      openApplyModal(btn);
    }
  });
})();


function showToast(message, level) { // level: success|danger|warning|info
  const stack = document.getElementById('toast-stack') || (() => {
    const d = document.createElement('div');
    d.id = 'toast-stack';
    d.className = 'position-fixed top-0 end-0 p-3';
    d.style.zIndex = 1200;
    document.body.appendChild(d);
    return d;
  })();

  const id = 'toast-' + String(Date.now());
  const div = document.createElement('div');
  div.id = id;
  div.className = `toast align-items-center text-bg-${level||'info'} border-0 mb-2`;
  div.setAttribute('role','alert'); div.setAttribute('aria-live','assertive'); div.setAttribute('aria-atomic','true');
  div.setAttribute('data-bs-delay','4000');
  div.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>`;
  stack.appendChild(div);
  new bootstrap.Toast(div).show();
}

