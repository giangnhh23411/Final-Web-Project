// Assets/JS/search.js
(() => {
  document.addEventListener('DOMContentLoaded', () => {
    // Gắn cho TẤT CẢ form có class .js-search-form
    document.querySelectorAll('.js-search-form').forEach(form => {
      const scope = (form.getAttribute('data-scope') || '').toLowerCase();
      const input = form.querySelector('.js-search-input');
      const resultsBox = document.getElementById('blogSearchResults') || form.querySelector('.js-search-results');

      // Đọc q từ URL (nếu có) -> tự lọc
      const urlQ = (new URL(location.href)).searchParams.get('q');
      if (urlQ && input) {
        input.value = urlQ;
        runSearch(scope, input.value.trim(), resultsBox);
      }

      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const q = (input?.value || '').trim();
        // Đẩy q vào URL (không reload trang)
        const u = new URL(location.href);
        if (q) u.searchParams.set('q', q); else u.searchParams.delete('q');
        window.history.replaceState({}, '', u);

        runSearch(scope, q, resultsBox);
      });
    });
  });

  function runSearch(scope, query, resultsBox) {
    if (scope === 'blog') {
      filterBlog(query, resultsBox);
    } else if (scope === 'shop') {
      // để dành cho trang shop-grid nếu cần
      filterProducts(query, resultsBox);
    }
  }

  /* ====== BLOG FILTER ====== */
  function filterBlog(query, resultsBox) {
    const posts = Array.from(document.querySelectorAll('.blog-post'));
    if (!posts.length) return;

    const q = query.toLowerCase();
    let shown = 0;

    posts.forEach(post => {
      // text có thể lấy từ dataset (nhanh) + tiêu đề + mô tả
      const ds = (post.dataset.title || '') + ' ' + (post.dataset.tags || '');
      const title = (post.querySelector('.post-title')?.textContent || '');
      const excerpt = (post.querySelector('.post-excerpt')?.textContent || '');
      const haystack = (ds + ' ' + title + ' ' + excerpt).toLowerCase();

      const isMatch = q === '' ? true : haystack.includes(q);
      post.style.display = isMatch ? '' : 'none';
      if (isMatch) shown++;
    });

    if (resultsBox) {
      if (!q) {
        resultsBox.textContent = '';
      } else if (shown > 0) {
        resultsBox.textContent = `Found ${shown} post(s) for “${query}”.`;
      } else {
        resultsBox.textContent = `No posts found for “${query}”.`;
      }
    }
  }

  /* ====== SHOP FILTER (tùy chọn, để sẵn) ====== */
  function filterProducts(query, resultsBox) {
    const cards = Array.from(document.querySelectorAll('.shop-card'));
    if (!cards.length) return;

    const q = query.toLowerCase();
    let shown = 0;

    cards.forEach(card => {
      const name = (card.querySelector('.shop-card-name')?.textContent || '');
      const price = (card.querySelector('.shop-card-price')?.textContent || '');
      const ds = (card.dataset.tags || '') + ' ' + (card.dataset.title || '');
      const haystack = (name + ' ' + price + ' ' + ds).toLowerCase();
      const isMatch = q === '' ? true : haystack.includes(q);
      card.style.display = isMatch ? '' : 'none';
      if (isMatch) shown++;
    });

    if (resultsBox) {
      if (!q) resultsBox.textContent = '';
      else resultsBox.textContent = shown > 0
        ? `Found ${shown} item(s) for “${query}”.`
        : `No items found for “${query}”.`;
    }
  }
})();
