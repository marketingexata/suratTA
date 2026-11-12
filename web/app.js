'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const cache = new Map();
  const zipInput = $('zipcode');
  const status = $('status');
  const choices = $('choices');
  const result = $('result');
  let timer = null;
  let counter = 0;

  function setStatus(message, type = '') {
    status.textContent = message;
    status.className = 'status ' + type;
  }
  function normalizedZip() {
    return zipInput.value.replace(/\D/g, '').slice(0, 7);
  }
  function setAddress(entry) {
    // [pref, city, town] for general entries.
    // [pref, city, town, organization, block/detail, 'office'] for office codes.
    const [pref, city, town, office = '', block = ''] = entry;
    $('prefecture').value = pref;
    $('city').value = city;
    $('town').value = town;
    $('office').value = office;
    $('office').parentElement.hidden = !office;
    $('detail').value = block || '';
    result.hidden = false;
    refreshFullAddress();
  }
  function refreshFullAddress() {
    const { value: pref } = $('prefecture');
    const { value: city } = $('city');
    const { value: town } = $('town');
    const { value: detail } = $('detail');
    const { value: office } = $('office');
    $('full-address').textContent = [pref,city,town,detail,office].filter(Boolean).join('');
  }
  function showChoices(entries) {
    choices.replaceChildren();
    if (entries.length === 1) {
      choices.hidden = true;
      setAddress(entries[0]);
      return;
    }
    choices.hidden = false;
    const label = document.createElement('div');
    label.className = 'choices-heading';
    label.textContent = `${entries.length} alamat ditemukan. Pilih yang sesuai:`;
    choices.appendChild(label);
    entries.forEach((entry, index) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'choice';
      item.textContent = `${index+1}. ${entry[0]}${entry[1]}${entry[2] || ''}${entry[4] || ''}`;
      if (entry[3]) {
        const info = document.createElement('small');
        info.textContent = ` — ${entry[3]}`;
        item.appendChild(info);
      }
      item.addEventListener('click', () => {
        setAddress(entry);
        setStatus('Alamat dipilih. Lengkapi nomor rumah / apartemen jika perlu.', 'success');
      });
      choices.appendChild(item);
    });
    setAddress(entries[0]);
  }
  async function getShard(prefix) {
    if (cache.has(prefix)) return cache.get(prefix);
    // Files live at the same origin (the GitHub Pages website).
    const response = await fetch(`./data/${prefix}.json`);
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    cache.set(prefix, data);
    return data;
  }
  async function lookup() {
    const token = ++counter;
    const code = normalizedZip();
    if (code.length !== 7) {
      result.hidden = true;
      choices.hidden = true;
      setStatus('Masukkan tepat 7 digit kode pos.');
      return;
    }
    $('find').disabled = true;
    setStatus('Mencari alamat…');
    try {
      const shard = await getShard(code.slice(0,3));
      if (token !== counter) return;
      const entries = shard?.[code.slice(3)] ?? [];
      if (!entries.length) {
        result.hidden = true;
        choices.hidden = true;
        setStatus('Kode pos tidak ditemukan. Periksa kembali 7 digitnya.', 'error');
      } else {
        showChoices(entries);
        setStatus(`${entries.length} alamat ditemukan.`, 'success');
      }
    } catch (e) {
      if (token !== counter) return;
      result.hidden = true;
      choices.hidden = true;
      setStatus('Data belum tersedia atau koneksi terganggu. Pastikan GitHub Actions berhasil deploy.', 'error');
      console.error('Postal code lookup failed:', e);
    } finally {
      if (token === counter) $('find').disabled = false;
    }
  }
  zipInput.addEventListener('input', () => {
    const raw = normalizedZip();
    if (raw.length <= 3) {
      // Preserve the user's editing intent, do not insert a dash too early.
      zipInput.value = raw;
    } else {
      zipInput.value = raw.slice(0,3) + '-' + raw.slice(3);
    }
    clearTimeout(timer);
    ++counter;
    $('find').disabled = false;
    if (raw.length === 7) timer = setTimeout(lookup, 220);
    else {
      result.hidden = true;
      choices.hidden = true;
      setStatus('Masukkan 7 digit untuk mencari alamat.');
    }
  });
  zipInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { clearTimeout(timer); lookup(); }
  });
  $('find').addEventListener('click', () => { clearTimeout(timer); lookup(); });
  $('detail').addEventListener('input', refreshFullAddress);
  $('copy').addEventListener('click', async () => {
    const address = $('full-address').textContent;
    try {
      await navigator.clipboard.writeText(address);
      setStatus('Alamat berhasil disalin.', 'success');
    } catch {
      setStatus('Gagal menyalin otomatis; silakan pilih teks alamat lalu salin.', 'error');
    }
  });
  fetch('./data/meta.json')
    .then((r) => r.ok ? r.json() : Promise.reject(new Error('No metadata')))
    .then((data) => {
      const when = data.generated_at_utc?.slice(0,10) || '-';
      $('updated').textContent = `Database: ${data.postal_codes.toLocaleString('id-ID')} kode pos · dibuat ${when}`;
    })
    .catch(() => $('updated').textContent = 'Database belum dibuat. Jalankan workflow GitHub Actions.');
})();
