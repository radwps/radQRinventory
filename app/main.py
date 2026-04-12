from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

import qrcode
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .airtable_store import build_airtable_store
from .config import settings
from .mock_store import build_mock_store
from .store import InventoryError, NotFoundError


BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title=settings.app_title)
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

VALID_ACTIONS = {'add', 'subtract', 'receive', 'undo_receive'}


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _build_store():
    if settings.store_mode == 'airtable':
        return build_airtable_store()
    return build_mock_store()


STORE = _build_store()


def qr_data_uri(text: str) -> str:
    image = qrcode.make(text)
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    encoded = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def page_context(request: Request, **kwargs: Any) -> dict[str, Any]:
    return {
        'request': request,
        'settings': settings,
        **kwargs,
    }


def render_part_scan(
    request: Request,
    sku: str,
    preferred_action: str = '',
    quantity: int = 1,
    operator: str = '',
    note: str = '',
    purchase_order_id: str = '',
    receive_mode: bool = False,
    po_units: int = 1,
    error: str | None = None,
    status_code: int = 200,
):
    try:
        part = STORE.get_part(sku)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    normalized_action = preferred_action if preferred_action in VALID_ACTIONS else ''
    receive_mode = bool(receive_mode or purchase_order_id or normalized_action in {'receive', 'undo_receive'})
    if preferred_action and preferred_action not in VALID_ACTIONS and not error:
        error = 'Unsupported action.'
    purchase_orders = STORE.list_purchase_orders() if hasattr(STORE, 'list_purchase_orders') else []
    return templates.TemplateResponse(
        request,
        'scan_part.html',
        page_context(
            request,
            part=part,
            preferred_action=normalized_action,
            quantity=max(1, int(quantity or 1)),
            operator=operator,
            note=note,
            purchase_order_id=purchase_order_id or '',
            purchase_orders=purchase_orders,
            receive_mode=receive_mode,
            po_units=max(1, int(po_units or 1)),
            error=error,
            title=f'Update {part.name}',
        ),
        status_code=status_code,
    )


def apply_part_submission(
    request: Request,
    sku: str,
    action: str,
    quantity: int,
    operator: str,
    note: str,
    purchase_order_id: str = '',
    receive_mode: bool = False,
    po_units: int = 1,
):
    try:
        part = STORE.get_part(sku)
        apply_kwargs = dict(
            sku=sku,
            action=action,
            quantity=int(quantity),
            operator=operator,
            note=note,
            source=f'qr:part:{sku}:{action}',
        )
        if receive_mode:
            actual_po_units = max(1, int(po_units or 1))
            parts_per_po_unit = max(1, int(getattr(part, 'parts_per_po_unit', 1) or 1))
            apply_kwargs['quantity'] = actual_po_units * parts_per_po_unit
            apply_kwargs['po_units'] = actual_po_units
        if settings.store_mode == 'airtable' or receive_mode:
            apply_kwargs['purchase_order_id'] = purchase_order_id or ''
        result = STORE.apply_part_action(**apply_kwargs)
        return templates.TemplateResponse(
            request,
            'success.html',
            page_context(
                request,
                result=result,
                title='Scan logged',
            ),
        )
    except InventoryError as exc:
        return render_part_scan(
            request,
            sku=sku,
            preferred_action=action,
            quantity=max(1, int(quantity or 1)),
            operator=operator,
            note=note,
            purchase_order_id=purchase_order_id or '',
            receive_mode=receive_mode,
            po_units=max(1, int(po_units or 1)),
            error=str(exc),
            status_code=400,
        )


@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    parts = STORE.list_parts()
    kits = STORE.list_kits() if settings.enable_kits else []
    transactions = STORE.list_transactions(limit=20)
    return templates.TemplateResponse(
        request,
        'dashboard.html',
        page_context(
            request,
            parts=parts,
            kits=kits,
            transactions=transactions,
            store_mode=settings.store_mode,
            title=settings.app_title,
        ),
    )


@app.get('/scan/part/{sku}', response_class=HTMLResponse)
def scan_part(request: Request, sku: str, action: str = Query(default=''), receive_mode: bool = Query(default=False)):
    return render_part_scan(request, sku=sku, preferred_action=action, receive_mode=receive_mode)


@app.post('/scan/part/{sku}', response_class=HTMLResponse)
def scan_part_submit(
    request: Request,
    sku: str,
    action: str = Form(...),
    quantity: int = Form(1),
    operator: str = Form(''),
    note: str = Form(''),
    purchase_order_id: str = Form(''),
    receive_mode: str = Form('0'),
    po_units: int = Form(1),
):
    return apply_part_submission(request, sku, action, quantity, operator, note, purchase_order_id, receive_mode in {'1', 'true', 'on', 'yes'}, po_units)


@app.get('/scan/part/{sku}/{action}', response_class=HTMLResponse)
def scan_part_legacy(request: Request, sku: str, action: str):
    return render_part_scan(request, sku=sku, preferred_action=action, receive_mode=action in {'receive', 'undo_receive'})


@app.post('/scan/part/{sku}/{action}', response_class=HTMLResponse)
def scan_part_submit_legacy(
    request: Request,
    sku: str,
    action: str,
    quantity: int = Form(1),
    operator: str = Form(''),
    note: str = Form(''),
    purchase_order_id: str = Form(''),
    receive_mode: str = Form('0'),
    po_units: int = Form(1),
):
    return apply_part_submission(request, sku, action, quantity, operator, note, purchase_order_id, receive_mode in {'1', 'true', 'on', 'yes'}, po_units)


@app.get('/scan/kit/{code}/{action}', response_class=HTMLResponse)
def scan_kit(request: Request, code: str, action: str):
    if not settings.enable_kits:
        raise HTTPException(status_code=404, detail='Kit scanning is disabled.')
    kit = STORE.get_kit(code)
    error = None
    if action not in VALID_ACTIONS:
        error = 'Unsupported action.'
    return templates.TemplateResponse(
        request,
        'scan_kit.html',
        page_context(
            request,
            kit=kit,
            action=action,
            error=error,
            title=f'{action.title()} {kit.name}',
        ),
    )


@app.post('/scan/kit/{code}/{action}', response_class=HTMLResponse)
def scan_kit_submit(
    request: Request,
    code: str,
    action: str,
    operator: str = Form(''),
    note: str = Form(''),
):
    if not settings.enable_kits:
        raise HTTPException(status_code=404, detail='Kit scanning is disabled.')
    kit = STORE.get_kit(code)
    try:
        result = STORE.apply_kit_action(
            code=code,
            action=action,
            operator=operator,
            note=note,
            source=f'qr:kit:{code}:{action}',
        )
        return templates.TemplateResponse(
            request,
            'success.html',
            page_context(
                request,
                result=result,
                title='Kit scan logged',
            ),
        )
    except InventoryError as exc:
        return templates.TemplateResponse(
            request,
            'scan_kit.html',
            page_context(
                request,
                kit=kit,
                action=action,
                error=str(exc),
                title=f'{action.title()} {kit.name}',
            ),
            status_code=400,
        )


@app.get('/labels', response_class=HTMLResponse)
def labels(request: Request, base_url: str | None = None):
    public_base = (base_url or settings.public_base_url or str(request.base_url)).rstrip('/')
    parts = STORE.list_parts()

    part_labels = []
    for part in parts:
        scan_url = f'{public_base}/scan/part/{part.sku}'
        part_labels.append(
            {
                'part': part,
                'scan_url': scan_url,
                'scan_qr': qr_data_uri(scan_url),
            }
        )

    kit_labels = []
    if settings.enable_kits:
        for kit in STORE.list_kits():
            subtract_url = f'{public_base}/scan/kit/{kit.code}/subtract'
            kit_labels.append(
                {
                    'kit': kit,
                    'subtract_url': subtract_url,
                    'subtract_qr': qr_data_uri(subtract_url),
                }
            )

    return templates.TemplateResponse(
        request,
        'labels.html',
        page_context(
            request,
            public_base=public_base,
            part_labels=part_labels,
            part_label_pages=chunked(part_labels, 16),
            kit_labels=kit_labels,
            title='Printable labels',
        ),
    )


@app.post('/demo/reset')
def reset_demo():
    if settings.store_mode != 'mock' or not hasattr(STORE, 'reset_from_seed'):
        return RedirectResponse(url='/', status_code=303)
    STORE.reset_from_seed()
    return RedirectResponse(url='/', status_code=303)


@app.get('/health')
def health():
    return {'ok': True, 'store_mode': settings.store_mode, 'enable_kits': settings.enable_kits}
