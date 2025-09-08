// Tabs intentional; minimal vanilla JS (Bootstrap optional).
(function(){
	const $ = (sel, root=document) => root.querySelector(sel);
	const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));
	async function post(url, data) {
	const csrf = $('input[name="csrfmiddlewaretoken"]')?.value;
	const body = new URLSearchParams(data || {});
	try {
		const r = await fetch(url, {
		method: 'POST',
		headers: {'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded','X-CSRFToken': csrf || ''},
		body
		});
		try {
		return await r.json();
		} catch(err) {
		console.error('Invalid JSON from', url, err);
		return {ok:false, error:'Invalid server response'};
		}
	} catch(err) {
		console.error('Network error posting to', url, err);
		return {ok:false, error:'Network error'};
	}
	}
	async function get(url) {
	try {
		const r = await fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}});
		return await r.text();
	} catch(err) {
		console.error('Network error fetching', url, err);
		return '';
	}
	}
	// Live ANSI preview for room desc
	const btnPrev = $('#preview-desc');
	if (btnPrev) {
	btnPrev.addEventListener('click', async () => {
		const src = $('[data-role="ansi-preview-source"]');
		if (!src) return;
		const res = await post(window.ROOMEDITOR_ANSI_PREVIEW_URL || '/roomeditor/ansi/preview/', {text: src.value});
		const box = $('#desc-preview');
		const body = $('#desc-preview-body');
		if (res && res.html && box && body) {
		body.innerHTML = res.html;
		box.style.display = '';
		}
	});
	}
	// Modal helpers
	const modal = $('#modalHost');
	const modalBody = $('#modalBody');
	let bsModal = null;
	function openModal(html) {
	modalBody.innerHTML = html;
	if (!bsModal) {
		bsModal = new bootstrap.Modal(modal);
	}
	bsModal.show();
	attachExitFormHandler();
	attachRoomFormHandler();
	}
	// Add Exit/Room actions (modal)
	document.addEventListener('click', async (e) => {
	const t = e.target;
	if (t.matches('[data-action="modal-new-exit"]')) {
		const roomId = t.getAttribute('data-room');
		const url = `/roomeditor/exit/new/${roomId}/`;
		const html = await get(url);
		openModal(html);
	}
	if (t.matches('[data-action="modal-edit-exit"]')) {
		const exId = t.getAttribute('data-exit');
		const url = `/roomeditor/exit/${exId}/edit/`;
		const html = await get(url);
		openModal(html);
	}
	if (t.matches('[data-action="delete-exit"]')) {
		const exId = t.getAttribute('data-exit');
		if (!confirm('Delete this exit?')) return;
		const res = await post(`/roomeditor/exit/${exId}/delete/`, {});
		if (res && res.ok) {
		const row = document.querySelector(`[data-exit-id="${exId}"]`);
		if (row) row.remove();
		} else if (res && res.error) {
		alert(res.error);
		}
	}
	if (t.matches('[data-action="modal-new-room"]')) {
		const html = await get('/roomeditor/rooms/new/');
		openModal(html);
	}
	if (t.matches('[data-action="delete-room"]')) {
		const roomId = t.getAttribute('data-room');
		if (!confirm('Delete this room?')) return;
		const res = await post(`/roomeditor/rooms/${roomId}/delete/`, {});
		if (res && res.ok) {
		const row = document.querySelector(`[data-room-id="${roomId}"]`);
		if (row) row.remove();
		} else if (res && res.error) {
		alert(res.error);
		}
	}
	});
	function attachExitFormHandler() {
	const form = $('#exit-form', modalBody);
	if (!form) return;
	form.addEventListener('submit', async (e) => {
		e.preventDefault();
		const data = Object.fromEntries(new FormData(form).entries());
		const url = form.getAttribute('action') || window.location.href;
		const res = await post(url, data);
		if (res && res.ok) {
		if (res.row_html) {
			const list = $('#exit-list');
			if (list) {
			list.insertAdjacentHTML('beforeend', res.row_html);
			}
		}
		bsModal && bsModal.hide();
		} else if (res && res.error) {
		alert(res.error);
		}
	});
	}
	function attachRoomFormHandler() {
	const form = $('#room-form', modalBody);
	if (!form) return;
	form.addEventListener('submit', async (e) => {
		e.preventDefault();
		const data = Object.fromEntries(new FormData(form).entries());
		const url = form.getAttribute('action') || window.location.href;
		const res = await post(url, data);
		if (res && res.ok) {
		if (res.row_html) {
			const list = $('#room-table-body');
			if (list) {
			list.insertAdjacentHTML('beforeend', res.row_html);
			}
		}
		bsModal && bsModal.hide();
		} else if (res && res.error) {
		alert(res.error);
		}
	});
	}
})();
