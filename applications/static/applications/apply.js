// Vanilla JS + Bootstrap 5
function showToast(message, level) { // level: success|danger|warning|info
  const stack = document.getElementById('toast-stack') || (() => {
    const d = document.createElement('div');
    d.id = 'toast-stack';
    d.className = 'position-fixed top-0 end-0 p-3';
    d.style.zIndex = '1200';
    document.body.appendChild(d);
    return d;
  })();

  const id = 'toast-' + String(Date.now());
  const div = document.createElement('div');
  div.id = id;
  div.className = `toast align-items-center text-bg-${level || 'info'} border-0 mb-2 shadow-sm`;
  div.setAttribute('role', 'alert');
  div.setAttribute('aria-live', 'assertive');
  div.setAttribute('aria-atomic', 'true');
  div.setAttribute('data-bs-delay', '4000');
  div.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>`;
  stack.appendChild(div);
  new bootstrap.Toast(div).show();
}
window.showToast = showToast;

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
    } else if (el.parentElement !== document.body) {
      // Always move to body root to escape any parent CSS overflow:hidden or stacking context
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

    // Prevent concurrent requests
    if (btn.dataset.loading === "true") return;
    btn.dataset.loading = "true";
    const originalHtml = btn.innerHTML;
    btn.classList.add("disabled");
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Loading...';

    try {
      const url = `/applications/apply/preview/?type=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}&next=${encodeURIComponent(nextUrl)}`;
      const res = await fetch(url, { credentials: "same-origin" });
      if (!res.ok) {
        showToast("Unable to load application details. Please try again.", "danger");
        return;
      }
      const html = await res.text();

      const host = ensureContainer();
      host.innerHTML = html;

      const modalEl = document.getElementById("applyModal");
      if (!modalEl) {
        showToast("Application modal markup could not be loaded.", "danger");
        return;
      }

      // Cleanup on hidden to prevent backdrop or scroll lock freeze
      modalEl.addEventListener('hidden.bs.modal', function () {
        document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
      });

      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();

      // handle submit via AJAX for a smoother UX
      const form = modalEl.querySelector("#applyForm");
      if (form) {
        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          const submitBtn = modalEl.querySelector('button[type="submit"][form="applyForm"]') || form.querySelector('button[type="submit"]');
          const origSubmitHtml = submitBtn ? submitBtn.innerHTML : null;
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Submitting...';
          }
          try {
            const fd = new FormData(form);
            const resp = await fetch(form.action, {
              method: "POST",
              body: fd,
              headers: { "X-CSRFToken": getCookie("csrftoken") }
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok && data.ok && data.redirect) {
              modal.hide();
              // Clean backdrop immediately before navigation
              document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
              window.location.href = data.redirect;
            } else {
              const errMsg = data.error || "Something went wrong. Please try again.";
              showToast(errMsg, "danger");
              if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = origSubmitHtml;
              }
            }
          } catch (err) {
            console.error("Apply submission failed:", err);
            showToast("Network error during submission. Please try again.", "danger");
            if (submitBtn) {
              submitBtn.disabled = false;
              submitBtn.innerHTML = origSubmitHtml;
            }
          }
        });
      }
    } catch (err) {
      console.error("Failed to open apply modal:", err);
      showToast("An unexpected error occurred. Please try again.", "danger");
    } finally {
      btn.dataset.loading = "false";
      btn.classList.remove("disabled");
      btn.innerHTML = originalHtml;
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
