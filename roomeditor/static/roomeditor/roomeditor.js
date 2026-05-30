// Tabs intentional; minimal vanilla JS with Bootstrap 4/5 fallback.
(function(){
	const qs = (sel, root=document) => root.querySelector(sel);

	function csrfToken() {
		const input = qs('input[name="csrfmiddlewaretoken"]');
		if (input && input.value) {
			return input.value;
		}
		const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
		return match ? decodeURIComponent(match[1]) : '';
	}

	async function post(url, data) {
		const body = new URLSearchParams(data || {});
		try {
			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'X-Requested-With': 'XMLHttpRequest',
					'Content-Type': 'application/x-www-form-urlencoded',
					'X-CSRFToken': csrfToken(),
				},
				body
			});
			try {
				return await response.json();
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
			const response = await fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}});
			return await response.text();
		} catch(err) {
			console.error('Network error fetching', url, err);
			return '';
		}
	}

	const btnPrev = qs('#preview-desc');
	if (btnPrev) {
		btnPrev.addEventListener('click', async () => {
			const src = qs('[data-role="ansi-preview-source"]');
			if (!src) return;
			const res = await post(window.ROOMEDITOR_ANSI_PREVIEW_URL || '/roomeditor/ansi/preview/', {text: src.value});
			const box = qs('#desc-preview');
			const body = qs('#desc-preview-body');
			if (res && res.html && box && body) {
				body.innerHTML = res.html;
				box.style.display = '';
			} else if (res && res.error) {
				alert(res.error);
			}
		});
	}

	const modal = qs('#modalHost');
	const modalBody = qs('#modalBody');
	let bs5Modal = null;

	function setModalVisible(visible) {
		if (!modal) return;
		if (window.bootstrap && window.bootstrap.Modal) {
			if (!bs5Modal) {
				bs5Modal = new window.bootstrap.Modal(modal);
			}
			visible ? bs5Modal.show() : bs5Modal.hide();
			return;
		}
		if (window.jQuery && typeof window.jQuery.fn.modal === 'function') {
			window.jQuery(modal).modal(visible ? 'show' : 'hide');
			return;
		}
		modal.style.display = visible ? 'block' : 'none';
		modal.classList.toggle('show', visible);
		modal.setAttribute('aria-hidden', visible ? 'false' : 'true');
	}

	function closeModal() {
		setModalVisible(false);
	}

	function openModal(html) {
		if (!modal || !modalBody || !html) return;
		modalBody.innerHTML = html;
		setModalVisible(true);
		attachExitFormHandler();
		attachRoomFormHandler();
		modal.querySelectorAll('[data-close-modal]').forEach(btn => {
			btn.addEventListener('click', closeModal, { once: true });
		});
	}

	function removeEmptyState(container, name) {
		if (!container) return;
		const empty = qs(`[data-empty-state="${name}"]`, container);
		if (empty) empty.remove();
	}

	document.addEventListener('click', async (event) => {
		const target = event.target.closest('[data-action]');
		if (!target) return;
		const action = target.getAttribute('data-action');

		if (action === 'modal-new-exit') {
			const roomId = target.getAttribute('data-room');
			openModal(await get(`/roomeditor/exit/new/${roomId}/`));
		}
		if (action === 'modal-edit-exit') {
			const exId = target.getAttribute('data-exit');
			openModal(await get(`/roomeditor/exit/${exId}/edit/`));
		}
		if (action === 'delete-exit') {
			const exId = target.getAttribute('data-exit');
			if (!confirm('Delete this exit?')) return;
			const res = await post(`/roomeditor/exit/${exId}/delete/`, {});
			if (res && res.ok) {
				const row = qs(`[data-exit-id="${exId}"]`);
				if (row) row.remove();
			} else if (res && res.error) {
				alert(res.error);
			}
		}
		if (action === 'modal-new-room') {
			openModal(await get('/roomeditor/rooms/new/'));
		}
		if (action === 'delete-room') {
			const roomId = target.getAttribute('data-room');
			if (!confirm('Delete this room?')) return;
			const res = await post(`/roomeditor/rooms/${roomId}/delete/`, {});
			if (res && res.ok) {
				const row = qs(`[data-room-id="${roomId}"]`);
				if (row) row.remove();
			} else if (res && res.error) {
				alert(res.error);
			}
		}
	});

	function attachExitFormHandler() {
		const form = qs('#exit-form', modalBody);
		if (!form) return;
		form.addEventListener('submit', async (event) => {
			event.preventDefault();
			const data = Object.fromEntries(new FormData(form).entries());
			const url = form.getAttribute('action') || window.location.href;
			const res = await post(url, data);
			if (res && res.ok) {
				if (res.row_html) {
					const exId = form.getAttribute('data-exit');
					const existing = exId ? qs(`[data-exit-id="${exId}"]`) : null;
					if (existing) {
						existing.outerHTML = res.row_html;
					} else {
						const list = qs('#exit-list');
						if (list) {
							removeEmptyState(list, 'exits');
							list.insertAdjacentHTML('beforeend', res.row_html);
						}
					}
				}
				closeModal();
			} else if (res && res.error) {
				alert(res.error);
			}
		}, { once: true });
	}

	function attachRoomFormHandler() {
		const form = qs('#room-form', modalBody);
		if (!form) return;
		form.addEventListener('submit', async (event) => {
			event.preventDefault();
			const data = Object.fromEntries(new FormData(form).entries());
			const url = form.getAttribute('action') || window.location.href;
			const res = await post(url, data);
			if (res && res.ok) {
				if (res.row_html) {
					const list = qs('#room-table-body');
					if (list) {
						removeEmptyState(list, 'rooms');
						list.insertAdjacentHTML('beforeend', res.row_html);
					}
				}
				closeModal();
			} else if (res && res.error) {
				alert(res.error);
			}
		}, { once: true });
	}
})();
