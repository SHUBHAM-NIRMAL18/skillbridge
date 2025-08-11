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
      window.location.href = `${loginUrl}?next=${encodeURIComponent(nextUrl)}`;
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
