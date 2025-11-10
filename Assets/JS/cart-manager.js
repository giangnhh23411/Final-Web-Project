// Cart Manager - Quản lý giỏ hàng
class CartManager {
    constructor() {
        this.cart = this.loadCart();
        this.updateCartIcon();
    }

    // Lưu giỏ hàng vào localStorage
    saveCart() {
        localStorage.setItem('phuclong_cart', JSON.stringify(this.cart));
        
        // Lưu giỏ hàng theo user ID nếu đã đăng nhập
        const currentUser = JSON.parse(localStorage.getItem('phuclong_current_user') || 'null');
        if (currentUser) {
            localStorage.setItem(`phuclong_cart_${currentUser.id}`, JSON.stringify(this.cart));
            console.log(`Saved cart for user ${currentUser.id}:`, this.cart);
        }
        
        this.updateCartIcon();
    }

    // Load giỏ hàng từ localStorage
    loadCart() {
        const savedCart = localStorage.getItem('phuclong_cart');
        return savedCart ? JSON.parse(savedCart) : [];
    }

    // Thêm sản phẩm vào giỏ hàng
    addToCart(product) {
        const existingItem = this.cart.find(item => item.id === product.id);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                image: product.image,
                quantity: 1
            });
        }
        
        this.saveCart();
        this.showSuccessMessage(product.name);
    }

    // Xóa sản phẩm khỏi giỏ hàng
    removeFromCart(productId) {
        this.cart = this.cart.filter(item => item.id !== productId);
        this.saveCart();
    }

    // Cập nhật số lượng sản phẩm
    updateQuantity(productId, quantity) {
        const item = this.cart.find(item => item.id === productId);
        if (item) {
            if (quantity <= 0) {
                this.removeFromCart(productId);
            } else {
                item.quantity = quantity;
                this.saveCart();
            }
        }
    }

    // Lấy tổng số sản phẩm trong giỏ hàng
    getTotalItems() {
        return this.cart.reduce((total, item) => total + item.quantity, 0);
    }

    // Lấy tổng giá trị giỏ hàng
    getTotalPrice() {
        return this.cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    }

    // Cập nhật icon giỏ hàng
    updateCartIcon() {
        const cartIcons = document.querySelectorAll('.cart-icon, .cart-link');
        const totalItems = this.getTotalItems();
        
        cartIcons.forEach(icon => {
            // Xóa badge cũ nếu có
            const existingBadge = icon.querySelector('.cart-badge');
            if (existingBadge) {
                existingBadge.remove();
            }
            
            // Thêm badge mới nếu có sản phẩm
            if (totalItems > 0) {
                const badge = document.createElement('span');
                badge.className = 'cart-badge';
                badge.textContent = totalItems;
                badge.style.cssText = `
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background-color: #fb2e86;
                    color: white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    font-size: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                `;
                icon.style.position = 'relative';
                icon.appendChild(badge);
            }
        });
    }

    // Hiển thị popup xác nhận
    showConfirmDialog(product) {
        console.log('showConfirmDialog called with product:', product);
        // Xóa modal cũ nếu có
        const existingModal = document.querySelector('.cart-confirm-modal');
        if (existingModal) {
            document.body.removeChild(existingModal);
        }

        const modal = document.createElement('div');
        modal.className = 'cart-confirm-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div class="modal-content" style="
                background: white;
                padding: 30px;
                border-radius: 8px;
                text-align: center;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            ">
                <h3 style="color: #0d0e43; margin-bottom: 20px; font-size: 20px;">
                    Thêm vào giỏ hàng
                </h3>
                <div style="margin-bottom: 20px;">
                    <img src="../Final-Web-Project/Home/images/${product.image}" alt="${product.name}" style="
                        width: 80px;
                        height: 80px;
                        object-fit: contain;
                        border-radius: 8px;
                        background-color: #f8f9fa;
                        padding: 8px;
                        margin-bottom: 15px;
                    ">
                    <p style="color: #666; font-size: 16px;">
                        Bạn có muốn thêm <strong>"${product.name}"</strong> vào giỏ hàng không?
                    </p>
                </div>
                <div style="display: flex; gap: 15px; justify-content: center;">
                    <button class="btn-cancel" style="
                        background-color: #f8f9fa;
                        color: #666;
                        border: 1px solid #ddd;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Không</button>
                    <button class="btn-confirm" style="
                        background-color: #fb2e86;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Có</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Event listeners
        modal.querySelector('.btn-cancel').addEventListener('click', () => {
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
        });

        modal.querySelector('.btn-confirm').addEventListener('click', () => {
            this.addToCart(product);
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
        });

        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                if (document.body.contains(modal)) {
                    document.body.removeChild(modal);
                }
            }
        });
    }

    // Hiển thị thông báo thành công
    showSuccessMessage(productName) {
        const notification = document.createElement('div');
        notification.className = 'cart-success-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 4px;
            z-index: 10001;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        notification.textContent = `Đã thêm "${productName}" vào giỏ hàng!`;

        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 3000);
    }

    // Chuyển đến trang giỏ hàng
    goToCart() {
        window.location.href = '../shopping-cart/index.html';
    }
}

// Khởi tạo Cart Manager
const cartManager = new CartManager();

// Hàm thêm sản phẩm vào giỏ hàng (để sử dụng trong HTML)
function addToCart(productId, productName, productPrice, productImage) {
    console.log('addToCart called:', {productId, productName, productPrice, productImage});
    
    // Kiểm tra đăng nhập
    const isLoggedIn = localStorage.getItem('phuclong_user_logged_in') === 'true';
    console.log('isLoggedIn:', isLoggedIn);
    
    if (!isLoggedIn) {
        console.log('Showing login dialog');
        showLoginDialog();
        return;
    }
    
    const product = {
        id: productId,
        name: productName,
        price: parseFloat(productPrice),
        image: productImage
    };
    
    console.log('Showing confirm dialog for product:', product);
    cartManager.showConfirmDialog(product);
}

// Hàm hiển thị popup đăng nhập
function showLoginDialog() {
    console.log('showLoginDialog called');
    const modal = document.createElement('div');
    modal.className = 'login-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        ">
            <h3 style="color: #0d0e43; margin-bottom: 20px; font-size: 20px;">
                Đăng nhập
            </h3>
            <form id="loginForm" style="text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Email:</label>
                    <input type="email" id="loginEmail" placeholder="Nhập email" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Mật khẩu:</label>
                    <input type="password" id="loginPassword" placeholder="Nhập mật khẩu" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 15px;">
                    <button type="button" class="btn-cancel" style="
                        background-color: #f8f9fa;
                        color: #666;
                        border: 1px solid #ddd;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Hủy</button>
                    <button type="submit" class="btn-login" style="
                        background-color: #fb2e86;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Đăng nhập</button>
                </div>
                <div style="text-align: center;">
                    <button type="button" class="btn-register" style="
                        background: none;
                        border: none;
                        color: #fb2e86;
                        cursor: pointer;
                        text-decoration: underline;
                        font-size: 14px;
                    ">Chưa có tài khoản? Đăng ký ngay</button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    modal.querySelector('.btn-cancel').addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    modal.querySelector('.btn-register').addEventListener('click', () => {
        document.body.removeChild(modal);
        showRegisterDialog();
    });

    modal.querySelector('#loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        
        try {
            const formData = new FormData();
            formData.append('email', email);
            formData.append('password', password);
            
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Lưu thông tin user
                localStorage.setItem('phuclong_user_logged_in', 'true');
                localStorage.setItem('phuclong_current_user', JSON.stringify(result.user));
                
                // Load cart từ API nếu có
                if (result.user && result.user.id) {
                    try {
                        const cartResponse = await fetch(`/api/carts?user_id=${result.user.id}`);
                        if (cartResponse.ok) {
                            const cartData = await cartResponse.json();
                            if (cartData.data && cartData.data.length > 0) {
                                const cartItems = cartData.data.map(item => ({
                                    id: item.product_id,
                                    sku: item.sku,
                                    name: item.product_name,
                                    price: item.unit_price,
                                    quantity: item.quantity,
                                    image: item.product_image || ''
                                }));
                                localStorage.setItem('phuclong_cart', JSON.stringify(cartItems));
                            }
                        }
                    } catch (cartError) {
                        console.error('Error loading cart:', cartError);
                    }
                }
                
                document.body.removeChild(modal);
                showSuccessMessage('Đăng nhập thành công!');
                
                // Redirect admin nếu có redirect_url
                if (result.redirect_url) {
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 500);
                } else {
                    // Reload page để cập nhật header
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                }
            } else {
                showErrorMessage(result.detail || 'Email hoặc mật khẩu không đúng!');
            }
        } catch (error) {
            console.error('Login error:', error);
            showErrorMessage('Đã xảy ra lỗi khi đăng nhập. Vui lòng thử lại!');
        }
    });

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Hàm hiển thị popup đăng ký
function showRegisterDialog() {
    console.log('showRegisterDialog called');
    const modal = document.createElement('div');
    modal.className = 'register-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            max-height: 90vh;
            overflow-y: auto;
        ">
            <h3 style="color: #0d0e43; margin-bottom: 20px; font-size: 20px;">
                Đăng ký tài khoản
            </h3>
            <form id="registerForm" style="text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Họ tên:</label>
                    <input type="text" id="registerName" placeholder="Nhập họ tên" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Tài khoản:</label>
                    <input type="text" id="registerUsername" placeholder="Nhập tài khoản" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Email:</label>
                    <input type="email" id="registerEmail" placeholder="Nhập email" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Số điện thoại:</label>
                    <input type="tel" id="registerPhone" placeholder="Nhập số điện thoại" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Mật khẩu:</label>
                    <input type="password" id="registerPassword" placeholder="Nhập mật khẩu" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: 600; color: #333;">Xác nhận mật khẩu:</label>
                    <input type="password" id="registerConfirmPassword" placeholder="Nhập lại mật khẩu" style="
                        width: 100%;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        font-size: 14px;
                    " required>
                </div>
                <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 15px;">
                    <button type="button" class="btn-cancel" style="
                        background-color: #f8f9fa;
                        color: #666;
                        border: 1px solid #ddd;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Hủy</button>
                    <button type="submit" class="btn-register" style="
                        background-color: #fb2e86;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Đăng ký</button>
                </div>
                <div style="text-align: center;">
                    <button type="button" class="btn-login" style="
                        background: none;
                        border: none;
                        color: #fb2e86;
                        cursor: pointer;
                        text-decoration: underline;
                        font-size: 14px;
                    ">Đã có tài khoản? Đăng nhập</button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    modal.querySelector('.btn-cancel').addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    modal.querySelector('.btn-login').addEventListener('click', () => {
        document.body.removeChild(modal);
        showLoginDialog();
    });

    modal.querySelector('#registerForm').addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('registerName').value;
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const phone = document.getElementById('registerPhone').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('registerConfirmPassword').value;
        
        if (password !== confirmPassword) {
            showErrorMessage('Mật khẩu xác nhận không khớp!');
            return;
        }
        
        if (registerUser(name, username, email, phone, password)) {
            document.body.removeChild(modal);
            showSuccessMessage('Đăng ký thành công! Vui lòng đăng nhập.');
            setTimeout(() => {
                showLoginDialog();
            }, 1000);
        } else {
            showErrorMessage('Tài khoản đã tồn tại!');
        }
    });

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Hàm hiển thị thông báo thành công
function showSuccessMessage(message) {
    const notification = document.createElement('div');
    notification.className = 'success-notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #28a745;
        color: white;
        padding: 15px 20px;
        border-radius: 4px;
        z-index: 10001;
        font-weight: 600;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

// Hàm hiển thị thông báo lỗi
function showErrorMessage(message) {
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #dc3545;
        color: white;
        padding: 15px 20px;
        border-radius: 4px;
        z-index: 10001;
        font-weight: 600;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

// Hàm chuyển đến giỏ hàng
function goToCart() {
    cartManager.goToCart();
}

// ===== QUẢN LÝ NGƯỜI DÙNG =====

// Hàm đăng ký người dùng
function registerUser(name, username, email, phone, password) {
    const users = JSON.parse(localStorage.getItem('phuclong_users') || '[]');
    
    // Kiểm tra tài khoản đã tồn tại
    if (users.find(user => user.username === username)) {
        return false;
    }
    
    // Tạo người dùng mới
    const newUser = {
        id: Date.now(),
        name: name,
        username: username,
        email: email,
        phone: phone,
        password: password, // Trong thực tế nên hash password
        createdAt: new Date().toISOString()
    };
    
    users.push(newUser);
    localStorage.setItem('phuclong_users', JSON.stringify(users));
    
    console.log('User registered:', newUser);
    console.log('All users:', users);
    return true;
}

// Hàm đăng nhập người dùng
function loginUser(username, password) {
    const users = JSON.parse(localStorage.getItem('phuclong_users') || '[]');
    const user = users.find(u => u.username === username && u.password === password);
    
    if (user) {
        // Lưu thông tin đăng nhập
        localStorage.setItem('phuclong_user_logged_in', 'true');
        localStorage.setItem('phuclong_current_user', JSON.stringify({
            id: user.id,
            name: user.name,
            username: user.username,
            email: user.email,
            phone: user.phone
        }));
        
        // Load lại giỏ hàng của người dùng này
        const userCart = JSON.parse(localStorage.getItem(`phuclong_cart_${user.id}`) || '[]');
        localStorage.setItem('phuclong_cart', JSON.stringify(userCart));
        
        console.log('User logged in:', user);
        console.log('Loaded cart for user:', userCart);
        return true;
    }
    
    return false;
}

// Hàm đăng xuất
function logoutUser() {
    // Lưu giỏ hàng của người dùng hiện tại trước khi đăng xuất
    const currentUser = JSON.parse(localStorage.getItem('phuclong_current_user') || 'null');
    const currentCart = JSON.parse(localStorage.getItem('phuclong_cart') || '[]');
    
    if (currentUser && currentCart.length > 0) {
        // Lưu giỏ hàng theo user ID
        localStorage.setItem(`phuclong_cart_${currentUser.id}`, JSON.stringify(currentCart));
        console.log(`Saved cart for user ${currentUser.id}:`, currentCart);
    }
    
    localStorage.removeItem('phuclong_user_logged_in');
    localStorage.removeItem('phuclong_current_user');
    localStorage.removeItem('phuclong_cart'); // Xóa giỏ hàng tạm thời
    console.log('User logged out');
}

// Hàm hiển thị thông tin lưu trữ dữ liệu
function showDataStorageInfo() {
    const modal = document.createElement('div');
    modal.className = 'data-storage-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    const users = JSON.parse(localStorage.getItem('phuclong_users') || '[]');
    const currentUser = JSON.parse(localStorage.getItem('phuclong_current_user') || 'null');
    const cart = JSON.parse(localStorage.getItem('phuclong_cart') || '[]');

    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            padding: 30px;
            border-radius: 8px;
            text-align: left;
            max-width: 600px;
            width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            max-height: 80vh;
            overflow-y: auto;
        ">
            <h3 style="color: #0d0e43; margin-bottom: 20px; font-size: 20px; text-align: center;">
                📊 Thông tin lưu trữ dữ liệu
            </h3>
            
            <div style="margin-bottom: 20px;">
                <h4 style="color: #333; margin-bottom: 10px;">📍 Nơi lưu trữ:</h4>
                <p style="color: #666; margin-bottom: 10px;">
                    <strong>Browser LocalStorage</strong> - Dữ liệu được lưu trữ trên máy tính của bạn
                </p>
                <p style="color: #666; font-size: 14px;">
                    Đường dẫn: <code>D:/Final-Web-Project/</code> (chỉ chứa code, không chứa dữ liệu)
                </p>
            </div>

            <div style="margin-bottom: 20px;">
                <h4 style="color: #333; margin-bottom: 10px;">👥 Người dùng đã đăng ký:</h4>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 10px;">
                    <strong>Số lượng:</strong> ${users.length} tài khoản
                </div>
                ${users.length > 0 ? `
                    <div style="max-height: 200px; overflow-y: auto;">
                        ${users.map(user => `
                            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 4px;">
                                <strong>${user.name}</strong> (${user.username})<br>
                                <small style="color: #666;">Email: ${user.email} | Phone: ${user.phone}</small>
                            </div>
                        `).join('')}
                    </div>
                ` : '<p style="color: #666;">Chưa có người dùng nào đăng ký</p>'}
            </div>

            <div style="margin-bottom: 20px;">
                <h4 style="color: #333; margin-bottom: 10px;">🔐 Người dùng hiện tại:</h4>
                ${currentUser ? `
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 4px;">
                        <strong>${currentUser.name}</strong> (${currentUser.username})<br>
                        <small style="color: #666;">Email: ${currentUser.email}</small>
                    </div>
                ` : '<p style="color: #666;">Chưa đăng nhập</p>'}
            </div>

            <div style="margin-bottom: 20px;">
                <h4 style="color: #333; margin-bottom: 10px;">🛒 Giỏ hàng:</h4>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 4px;">
                    <strong>Số sản phẩm:</strong> ${cart.length} sản phẩm<br>
                    <strong>Tổng tiền:</strong> ₫${cart.reduce((total, item) => total + (item.price * item.quantity), 0).toLocaleString()}
                </div>
            </div>

            <div style="text-align: center;">
                <button class="btn-close" style="
                    background-color: #fb2e86;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                ">Đóng</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listener
    modal.querySelector('.btn-close').addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Hàm xóa tất cả dữ liệu (để test)
function clearAllData() {
    if (confirm('Bạn có chắc chắn muốn xóa TẤT CẢ dữ liệu? (Người dùng, giỏ hàng, v.v.)')) {
        localStorage.removeItem('phuclong_users');
        localStorage.removeItem('phuclong_current_user');
        localStorage.removeItem('phuclong_user_logged_in');
        localStorage.removeItem('phuclong_cart');
        alert('Đã xóa tất cả dữ liệu!');
        location.reload();
    }
}

// Thêm các hàm debug vào window
window.showDataStorageInfo = showDataStorageInfo;
window.clearAllData = clearAllData;
window.debugCart = function() {
    console.log('=== CART DEBUG ===');
    console.log('localStorage phuclong_cart:', localStorage.getItem('phuclong_cart'));
    console.log('Parsed cart:', JSON.parse(localStorage.getItem('phuclong_cart') || '[]'));
    console.log('==================');
};

// Hàm debug để xem tất cả giỏ hàng của các user
window.debugAllCarts = function() {
    console.log('=== ALL USER CARTS DEBUG ===');
    const users = JSON.parse(localStorage.getItem('phuclong_users') || '[]');
    users.forEach(user => {
        const userCart = JSON.parse(localStorage.getItem(`phuclong_cart_${user.id}`) || '[]');
        console.log(`User ${user.username} (ID: ${user.id}):`, userCart);
    });
    console.log('Current active cart:', JSON.parse(localStorage.getItem('phuclong_cart') || '[]'));
    console.log('================================');
};

// Hàm toggle đăng nhập/đăng xuất
function toggleLogin() {
    const isLoggedIn = localStorage.getItem('phuclong_user_logged_in') === 'true';
    const loginStatus = document.getElementById('loginStatus');
    
    if (isLoggedIn) {
        // Hiển thị popup xác nhận đăng xuất
        showLogoutConfirmDialog();
    } else {
        // Hiển thị popup đăng nhập
        showLoginDialog();
    }
}

// Hàm hiển thị popup xác nhận đăng xuất
function showLogoutConfirmDialog() {
    const modal = document.createElement('div');
    modal.className = 'logout-confirm-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        ">
            <h3 style="color: #0d0e43; margin-bottom: 20px; font-size: 20px;">
                Xác nhận đăng xuất
            </h3>
            <p style="color: #666; margin-bottom: 20px;">
                Bạn có chắc chắn muốn đăng xuất không?
            </p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button class="btn-cancel" style="
                    background-color: #f8f9fa;
                    color: #666;
                    border: 1px solid #ddd;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                ">Hủy</button>
                <button class="btn-confirm-logout" style="
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 600;
                ">Đăng xuất</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    modal.querySelector('.btn-cancel').addEventListener('click', () => {
        document.body.removeChild(modal);
    });

    modal.querySelector('.btn-confirm-logout').addEventListener('click', () => {
        // Thực hiện đăng xuất
        logoutUser();
        const loginStatus = document.getElementById('loginStatus');
        loginStatus.textContent = 'Login';
        showSuccessMessage('Đã đăng xuất!');
        cartManager.updateCartIcon();
        
        document.body.removeChild(modal);
    });

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

// Cập nhật trạng thái đăng nhập khi trang load
function updateLoginStatus() {
    const isLoggedIn = localStorage.getItem('phuclong_user_logged_in') === 'true';
    const loginStatus = document.getElementById('loginStatus');
    
    if (loginStatus) {
        loginStatus.textContent = isLoggedIn ? 'Logout' : 'Login';
    }
}

// Cập nhật cart icon khi trang load
document.addEventListener('DOMContentLoaded', function() {
    cartManager.updateCartIcon();
    updateLoginStatus();
});
