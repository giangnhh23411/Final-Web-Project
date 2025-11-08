/* ==========================================================================
   Phuc Long - API-based Auth (Login / Register / Forgot)
   API Endpoints:
   - POST /api/auth/login - Login với email và password
   - POST /api/auth/register - Đăng ký user mới
   - GET /api/users/{email} - Kiểm tra email tồn tại (forgot password)
   
   Storage keys:
   - phuclong_user_logged_in: 'true' | undefined
   - phuclong_current_user: {id,name,username,email,phone,role}
   ========================================================================== */

(function () {
  const LS_USERS = 'phuclong_users';
  const LS_LOGGED = 'phuclong_user_logged_in';
  const LS_CURRENT = 'phuclong_current_user';
  const LS_CART = 'phuclong_cart';

  // ------------- Utilities (toast) -------------
  function toast(message, type = 'success', timeout = 2800) {
    const el = document.createElement('div');
    el.setAttribute('role', 'status');
    el.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 10000;
      background: ${type === 'error' ? '#dc3545' : type === 'info' ? '#0d6efd' : '#28a745'};
      color: #fff; padding: 12px 16px; border-radius: 6px; box-shadow: 0 6px 18px rgba(0,0,0,.2);
      font-weight: 600; font-size: 14px; max-width: 340px;
    `;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), timeout);
  }

  function getUsers() {
    try { return JSON.parse(localStorage.getItem(LS_USERS) || '[]'); }
    catch { return []; }
  }
  function saveUsers(arr) { localStorage.setItem(LS_USERS, JSON.stringify(arr)); }

  function setLoggedIn(user) {
    localStorage.setItem(LS_LOGGED, 'true');
    localStorage.setItem(LS_CURRENT, JSON.stringify({
      id: user.id, name: user.name, username: user.username,
      email: user.email, phone: user.phone
    }));
  }

  function logout() {
    const currentUser = JSON.parse(localStorage.getItem(LS_CURRENT) || 'null');
    const currentCart = JSON.parse(localStorage.getItem(LS_CART) || '[]');
    if (currentUser && currentCart?.length) {
      localStorage.setItem(`phuclong_cart_${currentUser.id}`, JSON.stringify(currentCart));
    }
    localStorage.removeItem(LS_LOGGED);
    localStorage.removeItem(LS_CURRENT);
    // Cart is kept to prevent surprising loss; clear if you want:
    // localStorage.removeItem(LS_CART);
    
    // Dispatch event để header cập nhật UI
    window.dispatchEvent(new Event('storage'));
  }

  function validateEmail(email) {
    return /^\S+@\S+\.\S+$/.test(email);
  }

  // ------------- Login flow -------------
  async function handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail')?.value.trim();
    const password = document.getElementById('loginPassword')?.value;
    const remember = document.getElementById('rememberMe')?.checked;

    if (!email || !password) {
      toast('Please fill your email and password.', 'error');
      return;
    }
    if (!validateEmail(email)) {
      toast('Email format is invalid.', 'error');
      return;
    }

    try {
      // Gọi API login
      const formData = new FormData();
      formData.append('email', email);
      formData.append('password', password);

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        toast(result.detail || 'Email or password is incorrect.', 'error');
        return;
      }

      // Login thành công
      const user = result.user;
      
      // Lưu user info vào LocalStorage (không có password)
      setLoggedIn({
        id: user._id || user.id,
        name: user.full_name || user.name,
        username: user.email,
        email: user.email,
        phone: user.phone || '',
        role: user.role || 'customer'
      });

      if (remember) {
        // Session đã được lưu trong LocalStorage
      }

      toast(`Welcome back, ${user.full_name || user.email || 'Guest'}!`);
      
      // Cập nhật UI header (nếu có)
      if (typeof updateLoginUI === 'function') {
        updateLoginUI();
      }
      
      // Dispatch event để header cập nhật UI
      window.dispatchEvent(new Event('storage'));
      
      // Điều hướng: về trang chủ hoặc quay về trang trước nếu có
      setTimeout(() => {
        const ref = document.referrer || '';
        if (ref && !ref.includes('my-account.html')) {
          window.location.replace(ref);
        } else {
          window.location.replace('/');
        }
      }, 650);
    } catch (error) {
      console.error('Login error:', error);
      toast('An error occurred. Please try again.', 'error');
    }
  }

  // ------------- Register modal -------------
  function openRegisterModal() {
    const existing = document.querySelector('.register-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'register-modal';
    modal.style.cssText = `
      position: fixed; inset: 0; background: rgba(0,0,0,.45);
      display: flex; align-items: center; justify-content: center; z-index: 9999;
    `;
    modal.innerHTML = `
      <div class="register-modal__content" style="
        background: #fff; width: min(520px, 92vw); max-height: 90vh; overflow:auto;
        border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,.25); padding: 20px 22px;
      ">
        <h3 style="margin:0 0 14px; color:#0d0e43;">Create account</h3>
        <form id="registerForm">
          <div style="display:grid; gap:12px;">
            <input id="regName" type="text" placeholder="Full name" required />
            <input id="regEmail" type="email" placeholder="Email" required />
            <input id="regPhone" type="tel" placeholder="Phone (optional)" />
            <input id="regPassword" type="password" placeholder="Password (min 4 chars)" minlength="4" required />
            <input id="regConfirm" type="password" placeholder="Confirm password" minlength="4" required />
          </div>
          <div style="display:flex; gap:10px; justify-content:flex-end; margin-top:16px;">
            <button type="button" id="btnRegCancel" style="
              background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;padding:8px 12px;cursor:pointer;
            ">Cancel</button>
            <button type="submit" style="
              background:#fb2e86;border:none;color:#fff;border-radius:6px;padding:8px 12px;cursor:pointer;font-weight:600;
            ">Create</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    modal.querySelector('#btnRegCancel').addEventListener('click', () => modal.remove());
    modal.querySelector('#registerForm').addEventListener('submit', handleRegisterSubmit);
  }

  async function handleRegisterSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const phone = document.getElementById('regPhone').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regConfirm').value;

    if (!name || !email || !password || !confirm) {
      toast('Please fill all required fields.', 'error');
      return;
    }
    if (!validateEmail(email)) {
      toast('Email format is invalid.', 'error');
      return;
    }
    if (password.length < 4) {
      toast('Password must be at least 4 characters.', 'error');
      return;
    }
    if (password !== confirm) {
      toast('Password confirmation does not match.', 'error');
      return;
    }

    try {
      // Gọi API register
      const formData = new FormData();
      formData.append('full_name', name);
      formData.append('email', email);
      if (phone) {
        formData.append('phone', phone);
      }
      formData.append('password', password);

      const response = await fetch('/api/auth/register', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (!response.ok) {
        toast(result.detail || 'Registration failed. Please try again.', 'error');
        return;
      }

      // Registration thành công
      toast('Account created successfully! Please sign in.', 'success');
      document.querySelector('.register-modal')?.remove();
      
      // Tự động điền email vào form login
      const loginEmail = document.getElementById('loginEmail');
      if (loginEmail) {
        loginEmail.value = email;
      }
    } catch (error) {
      console.error('Registration error:', error);
      toast('An error occurred. Please try again.', 'error');
    }
  }

  // ------------- Forgot password (demo) -------------
  async function handleForgotClick(e) {
    e.preventDefault();
    const email = (document.getElementById('loginEmail')?.value || '').trim();
    if (!email) {
      toast('Enter your email first, then click again.', 'info');
      return;
    }
    
    if (!validateEmail(email)) {
      toast('Email format is invalid.', 'error');
      return;
    }

    try {
      // Kiểm tra email có tồn tại không
      const response = await fetch(`/api/users/${encodeURIComponent(email)}`);
      
      if (!response.ok) {
        toast('This email is not registered.', 'error');
        return;
      }

      // Demo: chỉ báo thành công; không gửi email thật.
      toast('A reset instruction has been (hypothetically) sent to your email.', 'success');
    } catch (error) {
      console.error('Forgot password error:', error);
      toast('An error occurred. Please try again.', 'error');
    }
  }

  // Kiểm tra nếu đã đăng nhập thì redirect hoặc hiển thị thông báo
  function checkIfLoggedIn() {
    const isLoggedIn = localStorage.getItem(LS_LOGGED) === 'true';
    const currentUser = JSON.parse(localStorage.getItem(LS_CURRENT) || 'null');
    
    if (isLoggedIn && currentUser) {
      // Đã đăng nhập - có thể redirect hoặc hiển thị thông báo
      const loginForm = document.getElementById('loginForm');
      if (loginForm) {
        // Ẩn form login và hiển thị thông báo
        loginForm.style.display = 'none';
        const loginCard = document.querySelector('.login-card');
        if (loginCard) {
          const infoDiv = document.createElement('div');
          infoDiv.style.cssText = 'text-align: center; padding: 20px;';
          infoDiv.innerHTML = `
            <h3 style="color: #28a745; margin-bottom: 10px;">✓ Bạn đã đăng nhập!</h3>
            <p style="color: #6b7280; margin-bottom: 16px;">Hello, <strong>${currentUser.name || currentUser.email}</strong></p>
            <button onclick="window.PLAuth.logout(); window.location.reload();" style="
              background: #dc3545; color: #fff; border: none; border-radius: 8px;
              padding: 10px 20px; cursor: pointer; font-weight: 600;
            ">Logout</button>
          `;
          loginCard.appendChild(infoDiv);
        }
      }
    }
  }

  // ------------- Wiring -------------
  document.addEventListener('DOMContentLoaded', () => {
    // Kiểm tra trạng thái đăng nhập trước
    checkIfLoggedIn();
    
    const loginForm = document.getElementById('loginForm');
    const btnOpenReg = document.getElementById('openRegister');
    const forgotLink = document.getElementById('forgotLink');

    if (loginForm) loginForm.addEventListener('submit', handleLoginSubmit);
    if (btnOpenReg) btnOpenReg.addEventListener('click', (e) => { e.preventDefault(); openRegisterModal(); });
    if (forgotLink) forgotLink.addEventListener('click', handleForgotClick);
  });

  // Expose for console debug if needed
  window.PLAuth = { logout };
})();
