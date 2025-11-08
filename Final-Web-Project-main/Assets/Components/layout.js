// ========= PHUC LONG: HEADER/FOOTER LOADER =========
// Cách dùng trong mỗi trang:
// <div id="site-header"></div>
// <div id="site-footer"></div>
// <script src="/Assets/Components/layout.js" defer></script>

(function () {
  async function inject(url, sel) {
    const host = document.querySelector(sel);
    if (!host) return;
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(res.status + " " + res.statusText);
      host.innerHTML = await res.text();
    } catch (e) {
      console.error("Load component failed:", url, e);
      host.innerHTML = `<p style="text-align:center;color:red">Không tải được ${url}. Hãy kiểm tra đường dẫn.</p>`;
    }
  }

  function getAttrOr(defaultVal, ...names) {
    const s = document.currentScript;
    for (const n of names) {
      const v = s?.getAttribute(n);
      if (v) return v;
    }
    return defaultVal;
  }

  // Cho phép override bằng data-attributes, nếu không đặt thì dùng mặc định root-relative
  const headerUrl  = getAttrOr("/Assets/Components/header.html", "data-header");
  const footerUrl  = getAttrOr("/Assets/Components/footer.html", "data-footer");
  const headerHost = getAttrOr("#site-header", "data-header-target");
  const footerHost = getAttrOr("#site-footer", "data-footer-target");

  // Inject
  document.addEventListener("DOMContentLoaded", async () => {
    await inject(headerUrl, headerHost);
    await inject(footerUrl, footerHost);
    
    // Chạy lại các script trong header sau khi inject
    const headerElement = document.querySelector(headerHost);
    if (headerElement) {
      const scripts = headerElement.querySelectorAll('script');
      scripts.forEach(oldScript => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => {
          newScript.setAttribute(attr.name, attr.value);
        });
        newScript.textContent = oldScript.textContent;
        oldScript.parentNode.replaceChild(newScript, oldScript);
      });
    }
    
    // phát event để trang khác biết là header/footer đã sẵn sàng
    document.dispatchEvent(new CustomEvent("phuclong:hf-loaded"));
  });
})();
