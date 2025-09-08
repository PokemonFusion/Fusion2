// Tabs intentional; minimal vanilla JS (Bootstrap optional).
(function(){
    const $ = (sel, root=document) => root.querySelector(sel);
    const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

    function post(url, data) {
        const csrf = $('input[name="csrfmiddlewaretoken"]')?.value;
        const body = new URLSearchParams(data || {});
        return fetch(url, {
            method: 'POST',
            headers: {'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded','X-CSRFToken': csrf || ''},
            body
        }).then(r => r.json());
    }

    function get(url) {
        return fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}}).then(r => r.text());
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
            }
        }
        if (t.matches('[data-action="modal-new-room"]')) {
            const html = await get('/roomeditor/room/new/');
            openModal(html);
        }
        if (t.matches('[data-action="delete-room"]')) {
            const roomId = t.getAttribute('data-room');
            if (!confirm('Delete this room?')) return;
            const res = await post(`/roomeditor/room/${roomId}/delete/`, {});
            if (res && res.ok) {
                const row = document.querySelector(`[data-room-id="${roomId}"]`);
                if (row) row.remove();
            }
        }
    });

    function attachExitFormHandler() {
        const form = $('#exit-form', modalBody);
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = new URLSearchParams(new FormData(form));
            const url = form.getAttribute('action') || window.location.href;
            const res = await fetch(url, {
                method: 'POST',
                headers: {'X-Requested-With':'XMLHttpRequest'},
                body: data
            }).then(r => r.json());
            if (res && res.ok) {
                if (res.row_html) {
                    const list = $('#exit-list');
                    if (list) {
                        list.insertAdjacentHTML('beforeend', res.row_html);
                    }
                }
                bsModal && bsModal.hide();
            } else {
                // Replace body with returned form (if provided). Fallback to reload.
                location.reload();
            }
        });
    }

    function attachRoomFormHandler() {
        const form = $('#room-form', modalBody);
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = new URLSearchParams(new FormData(form));
            const url = form.getAttribute('action') || window.location.href;
            const res = await fetch(url, {
                method: 'POST',
                headers: {'X-Requested-With':'XMLHttpRequest'},
                body: data
            }).then(r => r.json());
            if (res && res.ok) {
                if (res.row_html) {
                    const list = $('#room-table-body');
                    if (list) {
                        list.insertAdjacentHTML('beforeend', res.row_html);
                    }
                }
                bsModal && bsModal.hide();
            } else {
                location.reload();
            }
        });
    }
})();
