// Assets/JS/map.js
// Store Locator cho Phúc Long — tách riêng JS
// Nhớ nhúng Google Maps JS ở index.html với callback=initLocatorMap

(() => {
  "use strict";

  // ====== DỮ LIỆU MẪU (có thể thay bằng fetch JSON của bạn) ======
  const SL_DATA = [
    { id:"HCM-LTT", name:"Phúc Long Lê Thánh Tôn", address:"63 Lê Thánh Tôn, Bến Nghé, Q.1, TP.HCM", province:"TP.HCM", district:"Quận 1", ward:"P. Bến Nghé", phone:"(028) 7100 1968", open:"07:00 - 22:30", status:"Mở cửa", lat:10.777094, lng:106.700615 },
    { id:"BD-CH44", name:"BDG-CH 44 Nguyễn Đình Chiểu PPC", address:"44 Nguyễn Đình Chiểu, P. Phú Cường, TP. Thủ Dầu Một, Bình Dương", province:"Bình Dương", district:"TP. Thủ Dầu Một", ward:"P. Phú Cường", phone:"(028) 7100 1968 (Ext.20028)", open:"07:00 - 22:30", status:"Đang hoạt động", lat:10.981975, lng:106.657549 },
    { id:"CTO-HV2", name:"CTO-CH Vincom Hùng Vương Số 2", address:"Vincom Hùng Vương Số 2, P. Thới Bình, Q. Ninh Kiều, Cần Thơ", province:"Cần Thơ", district:"Q. Ninh Kiều", ward:"P. Thới Bình", phone:"(029) 2384 4444", open:"07:00 - 22:00", status:"Đang hoạt động", lat:10.032571, lng:105.774984 },
    { id:"HN-HBT", name:"Phúc Long Hai Bà Trưng", address:"15 Hai Bà Trưng, Hoàn Kiếm, Hà Nội", province:"Hà Nội", district:"Hoàn Kiếm", ward:"Tràng Tiền", phone:"(024) 3936 8888", open:"07:00 - 22:00", status:"Mở cửa", lat:21.025487, lng:105.853667 }
  ];

  // ====== BIẾN TOÀN CỤC CHO MODULE NÀY ======
  let map, info, bounds, markers = [];
  let userPos = null;
  let current = [...SL_DATA];

  // ====== TIỆN ÍCH ======
  const $ = (s) => document.querySelector(s);
  const haversine = (a,b) => {
    const toRad = d => d * Math.PI / 180, R = 6371;
    const dLat = toRad(b.lat - a.lat), dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat), lat2 = toRad(b.lat);
    const h = Math.sin(dLat/2)**2 + Math.cos(lat1)*Math.cos(lat2)*Math.sin(dLng/2)**2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };

  function populateFilters(){
    const provinces = [...new Set(SL_DATA.map(s => s.province))].sort();
    const pSel = $('#sl-province');
    provinces.forEach(p => {
      const o = document.createElement('option');
      o.value = o.textContent = p;
      pSel.appendChild(o);
    });
  }

  function updateDistrictOptions(){
    const p = $('#sl-province').value;
    const dSel = $('#sl-district'); dSel.innerHTML = '<option value="">Quận/huyện</option>';
    const wSel = $('#sl-ward'); wSel.innerHTML = '<option value="">Phường/xã</option>';
    if(!p) return;
    const districts = [...new Set(SL_DATA.filter(s => s.province === p).map(s => s.district))].sort();
    districts.forEach(d => {
      const o = document.createElement('option');
      o.value = o.textContent = d;
      dSel.appendChild(o);
    });
  }

  function updateWardOptions(){
    const p = $('#sl-province').value;
    const d = $('#sl-district').value;
    const wSel = $('#sl-ward'); wSel.innerHTML = '<option value="">Phường/xã</option>';
    if(!p || !d) return;
    const wards = [...new Set(SL_DATA.filter(s => s.province===p && s.district===d).map(s => s.ward))].sort();
    wards.forEach(w => {
      const o = document.createElement('option');
      o.value = o.textContent = w;
      wSel.appendChild(o);
    });
  }

  function filterData(){
    const q = $('#sl-q').value.trim().toLowerCase();
    const p = $('#sl-province').value;
    const d = $('#sl-district').value;
    const w = $('#sl-ward').value;

    current = SL_DATA.filter(s => {
      const textOk = !q || s.name.toLowerCase().includes(q) || s.address.toLowerCase().includes(q);
      const pOk = !p || s.province === p;
      const dOk = !d || s.district === d;
      const wOk = !w || s.ward === w;
      return textOk && pOk && dOk && wOk;
    });

    renderList();
    renderMarkers();
  }

  function renderMarkers(){
    markers.forEach(m => m.setMap(null));
    markers = [];
    bounds = new google.maps.LatLngBounds();

    current.forEach(s => {
      const mk = new google.maps.Marker({ position: {lat:s.lat, lng:s.lng}, map, title: s.name });
      mk.addListener('click', () => {
        map.panTo(mk.getPosition());
        info.setContent(`
          <div style="max-width:260px">
            <strong>${s.name}</strong><br/>
            <div style="color:#6b7280">${s.address}</div>
            <div style="margin-top:6px">
              <a target="_blank" href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(s.lat+','+s.lng)}">Chỉ đường</a>
            </div>
          </div>
        `);
        info.open({ anchor: mk, map });
        const el = document.querySelector('[data-sl-id="'+s.id+'"]');
        if(el) el.scrollIntoView({behavior:'smooth', block:'start'});
      });
      markers.push(mk);
      bounds.extend(mk.getPosition());
    });

    if(current.length) map.fitBounds(bounds);
    $('#sl-count').textContent = current.length;
  }

  function renderList(){
    const list = $('#sl-list');
    list.innerHTML = '';
    if(!current.length){
      list.innerHTML = '<div style="padding:16px;color:#6b7280;text-align:center">Không tìm thấy cửa hàng phù hợp.</div>';
      return;
    }
    if(userPos && $('#sl-sort').dataset.active === '1'){
      current.sort((a,b)=>haversine(userPos,a)-haversine(userPos,b));
    }
    current.forEach(s=>{
      const dist = userPos ? `<span class="sl-distance">${haversine(userPos,s).toFixed(2)} km</span>` : '';
      const stCls = /mở|open|đang hoạt động/i.test(s.status) ? 'sl-status open' : 'sl-status';
      const item = document.createElement('div');
      item.className = 'sl-item';
      item.dataset.slId = s.id;
      item.innerHTML = `
        <div class="sl-avatar">PL</div>
        <div>
          <h3 style="margin:0 0 6px;font-size:16px">${s.name}</h3>
          <div class="sl-meta">
            <span class="${stCls}">● ${s.status || '—'}</span> ${dist}
            <div><strong>Địa chỉ:</strong> ${s.address}</div>
            <div><strong>SĐT:</strong> ${s.phone || '-'}</div>
            <div><strong>Giờ:</strong> ${s.open || '-'}</div>
            <div style="margin-top:8px">
              <a class="sl-btn" target="_blank" href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(s.lat+','+s.lng)}">🧭 Chỉ đường</a>
            </div>
          </div>
        </div>`;
      item.addEventListener('mouseenter',()=>{
        const m = markers.find(mm => mm.getTitle()===s.name);
        if(m){ m.setAnimation(google.maps.Animation.BOUNCE); setTimeout(()=>m.setAnimation(null),700); }
      });
      item.addEventListener('click',()=>{
        const m = markers.find(mm => mm.getTitle()===s.name);
        if(m){ map.panTo(m.getPosition()); map.setZoom(16); google.maps.event.trigger(m,'click'); }
      });
      list.appendChild(item);
    });
  }

  function locateMe(){
    return new Promise((resolve,reject)=>{
      if(!navigator.geolocation) return reject(new Error('Trình duyệt không hỗ trợ vị trí'));
      navigator.geolocation.getCurrentPosition(pos=>{
        userPos = {lat:pos.coords.latitude, lng:pos.coords.longitude};
        resolve(userPos);
      }, err=>reject(err), {enableHighAccuracy:true, timeout:10000, maximumAge:0});
    });
  }

  // ====== HÀM CALLBACK CHO GOOGLE MAPS ======
  window.initLocatorMap = () => {
    const el = document.getElementById('sl-map');
    if(!el) return; // không có section thì bỏ qua

    map = new google.maps.Map(el, { center:{lat:10.77,lng:106.69}, zoom:12 });
    info = new google.maps.InfoWindow();

    populateFilters();
    filterData();

    // events
    $('#sl-q').addEventListener('input', filterData);
    $('#sl-province').addEventListener('change', ()=>{ updateDistrictOptions(); filterData(); });
    $('#sl-district').addEventListener('change', ()=>{ updateWardOptions(); filterData(); });
    $('#sl-ward').addEventListener('change', filterData);
    $('#sl-clear').addEventListener('click', ()=>{
      $('#sl-q').value=''; $('#sl-province').value=''; $('#sl-district').innerHTML='<option value="">Quận/huyện</option>'; $('#sl-ward').innerHTML='<option value="">Phường/xã</option>';
      $('#sl-sort').dataset.active='0'; filterData();
    });
    $('#sl-locate').addEventListener('click', async ()=>{
      try{
        await locateMe();
        new google.maps.Marker({position:userPos,map,icon:{path:google.maps.SymbolPath.CIRCLE,scale:6,fillColor:'#2563eb',fillOpacity:1,strokeWeight:2,strokeColor:'#fff'},title:'Vị trí của bạn'});
        map.panTo(userPos);
        renderList();
      }catch(e){ alert('Không lấy được vị trí: '+e.message); }
    });
    $('#sl-sort').addEventListener('click', async (e)=>{
      if(!userPos){
        try{ await locateMe(); }catch(_){ alert('Cần quyền vị trí để sắp theo khoảng cách'); return; }
      }
      const btn = e.currentTarget;
      const active = btn.dataset.active === '1';
      btn.dataset.active = active ? '0' : '1';
      btn.classList.toggle('primary', !active);
      renderList();
    });
  };

})();
