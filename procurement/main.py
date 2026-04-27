import csv
import os
import re
import secrets
import statistics
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
CSV_PATH = os.path.join(DATA_DIR, "goszakup.csv")

os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="AI Procurement Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_LOTS = [
    {"lot_no": "ЗЦП-1001", "title": "Поставка ноутбуков HP ProBook 450 G9", "description": "Поставка ноутбуков HP ProBook 450 G9 — 25 шт. для нужд центрального аппарата. Гарантия 24 мес.", "qty": "25 шт.", "price": "12 500 000 KZT", "customer": "АО НК «КазМунайГаз»", "method": "Запрос ценовых предложений", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1002", "title": "Мониторы 27\" для офиса", "description": "Закуп мониторов 27\" — 40 шт., разрешение QHD, IPS-матрица.", "qty": "40 шт.", "price": "4 800 000 KZT", "customer": "ТОО «Казахтелеком»", "method": "Запрос ценовых предложений", "status": "Приём заявок"},
    {"lot_no": "ОТ-1003", "title": "Серверное оборудование Dell PowerEdge R750", "description": "Серверное оборудование Dell PowerEdge R750 с расширенной гарантией.", "qty": "3 шт.", "price": "32 000 000 KZT", "customer": "Министерство цифрового развития", "method": "Открытый тендер", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1004", "title": "Канцелярские товары на 2026 год", "description": "Канцелярские товары: бумага, ручки, папки и пр.", "qty": "1 партия", "price": "1 250 000 KZT", "customer": "Акимат г. Астана", "method": "Запрос ценовых предложений", "status": "Приём заявок"},
    {"lot_no": "ОТ-1005", "title": "Офисная мебель (столы, кресла)", "description": "Поставка офисной мебели: столы, кресла эргономичные.", "qty": "120 шт.", "price": "6 700 000 KZT", "customer": "АО «Самрук-Казына»", "method": "Открытый тендер", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1006", "title": "Спецодежда для рабочих", "description": "Спецодежда для рабочих нефтесервиса, сертифицированная.", "qty": "200 комплектов", "price": "9 100 000 KZT", "customer": "ТОО «KazMunayService»", "method": "Запрос ценовых предложений", "status": "Завершён"},
    {"lot_no": "ОТ-1007", "title": "УЗИ Mindray DC-70", "description": "Медицинское оборудование УЗИ Mindray DC-70 с принадлежностями.", "qty": "2 шт.", "price": "18 400 000 KZT", "customer": "ГКП «Городская больница №1»", "method": "Открытый тендер", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1008", "title": "Бумага А4 SvetoCopy", "description": "Закуп бумаги А4 SvetoCopy — 5000 пачек.", "qty": "5000 пачек", "price": "3 500 000 KZT", "customer": "Министерство образования РК", "method": "Запрос ценовых предложений", "status": "Приём заявок"},
    {"lot_no": "ОТ-1009", "title": "Автомобили Toyota Camry", "description": "Поставка автомобилей Toyota Camry — 5 шт. для служебного автопарка.", "qty": "5 шт.", "price": "42 000 000 KZT", "customer": "Управление делами Президента", "method": "Открытый тендер", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1010", "title": "Стройматериалы для ремонта школы", "description": "Строительные материалы для ремонта школы №7.", "qty": "1 партия", "price": "8 750 000 KZT", "customer": "Акимат Алматинской области", "method": "Запрос ценовых предложений", "status": "Приём заявок"},
    {"lot_no": "ОТ-1011", "title": "ПО Microsoft 365 — 200 лицензий", "description": "Программное обеспечение Microsoft 365 Business Standard — 200 лицензий, 1 год.", "qty": "200 лиц.", "price": "11 200 000 KZT", "customer": "АО «Казпочта»", "method": "Открытый тендер", "status": "Опубликован"},
    {"lot_no": "ЗЦП-1012", "title": "Кондиционеры Samsung", "description": "Поставка кондиционеров Samsung — 30 шт., с монтажом.", "qty": "30 шт.", "price": "5 400 000 KZT", "customer": "ТОО «Алматы Жылу»", "method": "Запрос ценовых предложений", "status": "Приём заявок"},
]

NOISE_WORDS = [
    "Текст", "История", "Подробнее", "Просмотр", "Скачать",
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for w in NOISE_WORDS:
        cleaned = cleaned.replace(w, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def make_short_title(text: str, limit: int = 80) -> str:
    if not text:
        return ""
    t = clean_text(text)
    for sep in ["—", " - ", ".", ","]:
        if sep in t:
            cand = t.split(sep)[0].strip()
            if 6 <= len(cand) <= limit:
                return cand
    return t[:limit] + ("..." if len(t) > limit else "")


def detect_method(text: str) -> str:
    t = (text or "").lower()
    if "тендер" in t:
        return "Открытый тендер"
    if "ценовых" in t or "зцп" in t:
        return "Запрос ценовых предложений"
    if "аукцион" in t:
        return "Аукцион"
    return "Запрос ценовых предложений"


def detect_status(text: str) -> str:
    t = (text or "").lower()
    if "заверш" in t:
        return "Завершён"
    if "приём" in t or "прием" in t:
        return "Приём заявок"
    if "отмен" in t:
        return "Отменён"
    return "Опубликован"


def parse_goszakup(product: str):
    try:
        import requests
        from bs4 import BeautifulSoup

        url = "https://goszakup.gov.kz/ru/search/lots"
        res = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=12,
            params={"filter[name]": product} if product else None,
        )

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", {"id": "search-result"}) or soup.find("table")
        if not table:
            raise Exception("table not found")

        rows = table.find_all("tr")
        data = []
        for row in rows[1:50]:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue

            lot_no_cell = clean_text(cols[0].get_text(" ", strip=True))
            announce_cell = clean_text(cols[1].get_text(" ", strip=True))
            name_cell = clean_text(cols[2].get_text(" ", strip=True))
            qty_cell = clean_text(cols[3].get_text(" ", strip=True))
            price_cell = clean_text(cols[4].get_text(" ", strip=True))
            method_cell = clean_text(cols[5].get_text(" ", strip=True))
            status_cell = clean_text(cols[6].get_text(" ", strip=True))

            lot_no_match = re.match(r"(\d+-[A-Za-zА-Яа-я0-9]+)", lot_no_cell)
            lot_no = lot_no_match.group(1) if lot_no_match else lot_no_cell.split()[0][:30]

            announce_link = cols[0].find("a") or cols[1].find("a")
            announce_id = ""
            if announce_link and announce_link.get("href"):
                m = re.search(r"/announce/index/(\d+)", announce_link["href"])
                if m:
                    announce_id = m.group(1)

            customer_match = re.search(r"Заказчик:\s*(.+)$", announce_cell)
            customer = clean_text(customer_match.group(1))[:200] if customer_match else clean_text(announce_cell)[:200]

            title = name_cell or make_short_title(announce_cell, 80) or "Без названия"
            description = announce_cell

            price_num = re.sub(r"[^\d.,]", "", price_cell).replace(" ", "")
            price = (price_cell + " ₸") if price_cell else "N/A"

            if not title:
                continue
            haystack = (title + " " + customer + " " + description).lower()
            if product and product.lower() not in haystack:
                continue

            data.append({
                "lot_no": lot_no,
                "announce_id": announce_id,
                "title": make_short_title(title, 80),
                "description": description[:800],
                "qty": qty_cell or "1",
                "price": price,
                "customer": customer or "N/A",
                "method": method_cell or detect_method(announce_cell),
                "status": status_cell or detect_status(announce_cell),
            })

        if not data:
            raise Exception("no rows matched")
        return data
    except Exception:
        return None


def parse_lot_detail(announce_id: str):
    try:
        import requests
        from bs4 import BeautifulSoup
        url = f"https://goszakup.gov.kz/ru/announce/index/{announce_id}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")

        block = soup.select_one("#main-wrapper .content-block") or soup.select_one(".content-block") or soup.find("body")
        text = clean_text(block.get_text(" ", strip=True)) if block else ""

        kv = {}
        for tr in soup.select("table tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) == 2:
                k = clean_text(tds[0].get_text(" ", strip=True)).rstrip(":").lower()
                v = clean_text(tds[1].get_text(" ", strip=True))
                if k and v and len(v) < 500:
                    kv[k] = v

        def find_kv(*keywords):
            for k, v in kv.items():
                if any(kw in k for kw in keywords):
                    return v
            return ""

        customer = find_kv("заказчик", "наименование организатора", "организатор")
        method = find_kv("способ проведения закупки", "способ закупки", "способ")
        status = find_kv("статус")
        quantity = find_kv("кол-во", "количество")

        sections = {
            "general": [],
            "customer": [],
            "address": [],
            "contacts": [],
            "description": [],
        }
        general_keys = ["способ", "тип закупки", "вид предмета", "номер", "дата", "срок", "статус", "сумма", "кол-во", "количество"]
        customer_keys = ["заказчик", "организатор", "наименование организ", "бин", "иин"]
        address_keys = ["адрес", "регион", "город", "место поставки", "место выполнения"]
        contact_keys = ["фио", "должность", "телефон", "e-mail", "email", "контакт"]
        desc_keys = ["описание", "характеристика", "наименование лота", "техническая спецификация", "условия"]

        for k, v in kv.items():
            label = k.capitalize()
            placed = False
            for kw in customer_keys:
                if kw in k: sections["customer"].append({"label": label, "value": v}); placed = True; break
            if placed: continue
            for kw in address_keys:
                if kw in k: sections["address"].append({"label": label, "value": v}); placed = True; break
            if placed: continue
            for kw in contact_keys:
                if kw in k: sections["contacts"].append({"label": label, "value": v}); placed = True; break
            if placed: continue
            for kw in desc_keys:
                if kw in k: sections["description"].append({"label": label, "value": v}); placed = True; break
            if placed: continue
            for kw in general_keys:
                if kw in k: sections["general"].append({"label": label, "value": v}); placed = True; break

        docs = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"]):
                docs.append({"name": clean_text(a.get_text(" ", strip=True))[:120] or href.split("/")[-1], "url": href if href.startswith("http") else "https://goszakup.gov.kz" + href})
            if len(docs) >= 10:
                break

        title_el = soup.find("h1") or soup.find("h2")
        title = clean_text(title_el.get_text(" ", strip=True))[:200] if title_el else ""

        return {
            "announce_id": announce_id,
            "url": url,
            "title": title,
            "description": text[:2000],
            "customer": customer,
            "quantity": quantity,
            "method": method,
            "status": status,
            "documents": docs,
            "sections": sections,
        }
    except Exception:
        return None


CSV_FIELDS = ["lot_no", "announce_id", "title", "description", "qty", "price", "customer", "method", "status"]


def save_csv(rows):
    try:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    except Exception:
        pass


def load_csv(product: Optional[str] = None):
    if not os.path.exists(CSV_PATH):
        return None
    try:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [dict(r) for r in reader]
        if product:
            p = product.lower()
            rows = [r for r in rows if p in (r.get("title", "") + " " + r.get("description", "")).lower()]
        return rows or None
    except Exception:
        return None


def get_demo(product: Optional[str] = None):
    if not product:
        return list(DEMO_LOTS)
    p = product.lower()
    matched = [d for d in DEMO_LOTS if p in (d["title"] + " " + d.get("description", "")).lower()]
    return matched or list(DEMO_LOTS)


def get_lots(product: str):
    rows = parse_goszakup(product)
    if rows:
        save_csv(rows)
        return rows, "live"

    rows = load_csv(product)
    if rows:
        return rows, "cache"

    return get_demo(product), "demo"


_LAST_RESULT_CACHE = {"rows": [], "product": ""}


def _price_to_number(price_str: str) -> Optional[float]:
    if not price_str or price_str == "N/A":
        return None
    cleaned = re.sub(r"[^\d,.]", "", str(price_str)).replace(",", ".")
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(cleaned) if cleaned else None
    except Exception:
        return None


def _qty_to_number(qty_str: str) -> int:
    if not qty_str:
        return 1
    m = re.search(r"\d+", str(qty_str))
    try:
        n = int(m.group(0)) if m else 1
        return max(1, n)
    except Exception:
        return 1


@app.get("/goszakup/lots")
def goszakup_lots(product: str = ""):
    rows, source = get_lots(product)
    _LAST_RESULT_CACHE["rows"] = rows
    _LAST_RESULT_CACHE["product"] = product
    return {"data": rows, "source": source, "count": len(rows)}


@app.get("/goszakup/refresh")
def goszakup_refresh(product: str = ""):
    try:
        if os.path.exists(CSV_PATH):
            os.remove(CSV_PATH)
    except Exception:
        pass
    _LAST_RESULT_CACHE["rows"] = []
    rows, source = get_lots(product)
    _LAST_RESULT_CACHE["rows"] = rows
    _LAST_RESULT_CACHE["product"] = product
    return {"data": rows, "source": source, "count": len(rows), "refreshed": True}


@app.get("/goszakup/detail/{announce_id}")
def goszakup_detail(announce_id: str):
    detail = parse_lot_detail(announce_id)
    if detail:
        return {"data": detail, "source": "live"}
    rows = _LAST_RESULT_CACHE.get("rows") or []
    fallback = next((r for r in rows if str(r.get("announce_id")) == str(announce_id)), None)
    if fallback:
        return {"data": {
            "announce_id": announce_id,
            "url": f"https://goszakup.gov.kz/ru/announce/index/{announce_id}",
            "title": fallback.get("title", ""),
            "description": fallback.get("description", ""),
            "customer": fallback.get("customer", ""),
            "quantity": fallback.get("qty", ""),
            "method": fallback.get("method", ""),
            "status": fallback.get("status", ""),
            "documents": [],
        }, "source": "cache"}
    raise HTTPException(status_code=404, detail="Лот не найден")


@app.get("/goszakup/analyze/{index}")
def goszakup_analyze(index: int):
    rows = _LAST_RESULT_CACHE.get("rows") or get_demo()
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail="Лот не найден")

    lot = rows[index]
    prices = [p for p in (_price_to_number(r.get("price", "")) for r in rows) if p is not None]

    if prices:
        avg_price = round(statistics.mean(prices), 2)
        min_price = min(prices)
        max_price = max(prices)
        status = "ok"
        explanation = (
            f"На основе {len(prices)} сопоставимых лотов средняя цена составляет "
            f"{avg_price:,.0f} KZT. Минимальная — {min_price:,.0f}, максимальная — {max_price:,.0f}."
        )
    else:
        avg_price = 50000.0
        min_price = 30000.0
        max_price = 80000.0
        status = "estimated"
        explanation = "Цены в исходных данных недоступны. Использована оценочная вилка."

    return {
        "lot": lot,
        "avg": avg_price,
        "min": min_price,
        "max": max_price,
        "status": status,
        "explanation": explanation,
        "sample_size": len(prices),
    }


TAX_RATE = 0.12


def search_suppliers(product: str, unit_price: float, quantity: int, lot_total: float):
    import random
    rng = random.Random(hash(product) & 0xFFFFFFFF)

    if not unit_price or unit_price <= 0:
        unit_price = 50000.0

    profiles = [
        {"name": f"Kaspi.kz — продавец «{product[:30] or 'Товар'}»", "factor": 0.78, "days": 3,  "reliability": 92, "source": "Kaspi",    "contact": "+7 727 000 00 01"},
        {"name": "Wildberries KZ — оптовый поставщик",                "factor": 0.85, "days": 5,  "reliability": 85, "source": "WB",       "contact": "+7 727 000 00 02"},
        {"name": "Alibaba — Shenzhen Trading Co., Ltd.",              "factor": 0.55, "days": 18, "reliability": 72, "source": "Alibaba",  "contact": "supplier@shenzhen-tc.cn"},
        {"name": "Satu.kz — локальный дистрибьютор",                  "factor": 0.92, "days": 4,  "reliability": 88, "source": "Satu",     "contact": "+7 727 000 00 04"},
    ]

    suppliers = []
    for p in profiles:
        ppu = round(unit_price * p["factor"])
        total = ppu * quantity
        delivery = rng.randrange(5000, 50001, 1000)
        full_cost = total + delivery
        profit = lot_total - full_cost
        tax = round(profit * TAX_RATE) if profit > 0 else 0
        net_profit = profit - tax
        suppliers.append({
            "name": p["name"],
            "source": p["source"],
            "contact": p["contact"],
            "delivery_days": p["days"],
            "reliability": p["reliability"],
            "price_per_unit": ppu,
            "quantity": quantity,
            "total": total,
            "delivery_cost": delivery,
            "full_cost": full_cost,
            "profit": profit,
            "tax": tax,
            "net_profit": net_profit,
            "margin_pct": round((net_profit / lot_total * 100) if lot_total > 0 else 0, 1),
        })
    return suppliers


@app.get("/goszakup/suppliers/{index}")
def goszakup_suppliers(index: int):
    rows = _LAST_RESULT_CACHE.get("rows") or get_demo()
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail="Лот не найден")

    lot = rows[index]
    product_query = (lot.get("title") or lot.get("description") or "").split("—")[0].strip()[:60] or "товар"
    lot_total = _price_to_number(lot.get("price", "")) or 0.0
    quantity = _qty_to_number(lot.get("qty", "1"))
    unit_price = (lot_total / quantity) if quantity > 0 and lot_total > 0 else 50000.0

    suppliers = search_suppliers(product_query, unit_price, quantity, lot_total)
    best = max(suppliers, key=lambda s: s["net_profit"])

    if best["net_profit"] > 0:
        explanation = (
            f"Лучший выбор — «{best['name']}» ({best['source']}). "
            f"Цена закупа {best['price_per_unit']:,} ₸/ед × {quantity} = {best['total']:,} ₸, "
            f"доставка {best['delivery_cost']:,} ₸. "
            f"Прибыль: {best['profit']:,} ₸, налог 12%: {best['tax']:,} ₸. "
            f"Чистая прибыль: {best['net_profit']:,} ₸ (маржа {best['margin_pct']}%)."
        )
    else:
        explanation = (
            f"Среди {len(suppliers)} поставщиков ни один не даёт прибыли при текущей цене лота. "
            f"Минимальный убыток у «{best['name']}»: {best['net_profit']:,} ₸. "
            f"Рекомендуется отказаться от участия или искать дешевле."
        )

    return {
        "lot": lot,
        "lot_total": lot_total,
        "lot_quantity": quantity,
        "lot_unit_price": round(unit_price),
        "suppliers": suppliers,
        "recommended": best,
        "explanation": explanation,
        "tax_rate": TAX_RATE,
    }


from db import db_session, User, Session as DBSession, Application as DBApp, Invoice as DBInvoice, SupplierProduct, hash_password, verify_password


class AuthPayload(BaseModel):
    username: str
    password: str
    role: Optional[str] = "buyer"
    market_type: Optional[str] = "retail"


class ApplyPayload(BaseModel):
    lot_index: int
    supplier_name: str
    supplier_price: float
    net_profit: Optional[float] = 0
    supplier_id: Optional[int] = None


class StatusPayload(BaseModel):
    status: str


class ResetPayload(BaseModel):
    username: str


class ResetConfirmPayload(BaseModel):
    token: str
    new_password: str


class ProductPayload(BaseModel):
    name: str
    category: Optional[str] = ""
    price: float = 0


def get_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    return authorization.replace("Bearer ", "").strip()


def get_user(authorization: Optional[str]):
    token = get_token(authorization)
    if not token:
        return None
    with db_session() as s:
        sess = s.get(DBSession, token)
        if not sess:
            return None
        u = s.get(User, sess.user_id)
        if not u:
            return None
        return {"id": u.id, "username": u.username, "role": u.role, "market_type": u.market_type}


def require_user(authorization):
    u = get_user(authorization)
    if not u:
        raise HTTPException(status_code=401, detail="Требуется вход в систему")
    return u


def serialize_app(a: DBApp) -> dict:
    return {
        "id": a.id, "buyer_id": a.buyer_id, "supplier_id": a.supplier_id,
        "lot_no": a.lot_no, "product": a.product, "customer": a.customer,
        "supplier": a.supplier_name, "quantity": a.quantity, "price": a.price,
        "net_profit": a.net_profit, "status": a.status, "statusKey": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def serialize_invoice(inv: DBInvoice) -> dict:
    return {
        "id": inv.id, "number": inv.number, "application_id": inv.application_id,
        "product": inv.product, "quantity": inv.quantity, "unit_price": inv.unit_price,
        "total": inv.total, "supplier_name": inv.supplier_name, "customer_name": inv.customer_name,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@app.post("/register")
def register(payload: AuthPayload):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Логин и пароль обязательны")
    role = payload.role if payload.role in ("buyer", "supplier") else "buyer"
    market = payload.market_type if payload.market_type in ("retail", "wholesale") else "retail"
    with db_session() as s:
        if s.query(User).filter_by(username=payload.username).first():
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        u = User(username=payload.username, password_hash=hash_password(payload.password), role=role, market_type=market)
        s.add(u); s.flush()
        token = secrets.token_hex(16)
        s.add(DBSession(token=token, user_id=u.id))
        return {"status": "ok", "token": token, "username": u.username, "role": u.role, "market_type": u.market_type}


@app.post("/login")
def login(payload: AuthPayload):
    with db_session() as s:
        u = s.query(User).filter_by(username=payload.username).first()
        if not u or not verify_password(payload.password, u.password_hash):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        token = secrets.token_hex(16)
        s.add(DBSession(token=token, user_id=u.id))
        return {"status": "ok", "token": token, "username": u.username, "role": u.role, "market_type": u.market_type}


@app.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(None)):
    u = get_user(authorization)
    if not u:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return u


@app.post("/auth/logout")
def auth_logout(authorization: Optional[str] = Header(None)):
    token = get_token(authorization)
    if token:
        with db_session() as s:
            sess = s.get(DBSession, token)
            if sess: s.delete(sess)
    return {"status": "ok"}


@app.post("/auth/reset")
def auth_reset(payload: ResetPayload):
    with db_session() as s:
        u = s.query(User).filter_by(username=payload.username).first()
        if not u:
            return {"status": "ok", "message": "Если пользователь существует, токен создан"}
        u.reset_token = secrets.token_hex(8)
        return {"status": "ok", "reset_token": u.reset_token, "message": "Сохраните токен для смены пароля"}


@app.post("/auth/reset/confirm")
def auth_reset_confirm(payload: ResetConfirmPayload):
    with db_session() as s:
        u = s.query(User).filter_by(reset_token=payload.token).first()
        if not u:
            raise HTTPException(status_code=400, detail="Неверный токен")
        u.password_hash = hash_password(payload.new_password)
        u.reset_token = None
        return {"status": "ok"}


@app.delete("/auth/account")
def auth_delete(authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    with db_session() as s:
        s.query(DBSession).filter_by(user_id=user["id"]).delete()
        s.query(DBApp).filter_by(buyer_id=user["id"]).delete()
        s.query(SupplierProduct).filter_by(supplier_id=user["id"]).delete()
        u = s.get(User, user["id"])
        if u: s.delete(u)
    return {"status": "ok"}


@app.post("/apply")
def apply(payload: ApplyPayload, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    if user["role"] != "buyer":
        raise HTTPException(status_code=403, detail="Только закупщик может подавать заявки")
    rows = _LAST_RESULT_CACHE.get("rows") or get_demo()
    if payload.lot_index < 0 or payload.lot_index >= len(rows):
        raise HTTPException(status_code=404, detail="Лот не найден")
    lot = rows[payload.lot_index]
    qty = _qty_to_number(lot.get("qty", "1"))
    with db_session() as s:
        a = DBApp(
            buyer_id=user["id"], supplier_id=payload.supplier_id,
            supplier_name=payload.supplier_name, lot_no=lot.get("lot_no", ""),
            product=lot.get("title", ""), customer=lot.get("customer", ""),
            quantity=qty, price=payload.supplier_price, net_profit=payload.net_profit or 0,
            status="sent",
        )
        s.add(a); s.flush()
        return {"status": "submitted", "application": serialize_app(a)}


@app.get("/applications")
def list_applications(authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    with db_session() as s:
        if user["role"] == "supplier":
            q = s.query(DBApp).filter((DBApp.supplier_id == user["id"]) | (DBApp.supplier_name.like(f"%{user['username']}%")))
        else:
            q = s.query(DBApp).filter_by(buyer_id=user["id"])
        apps = q.order_by(DBApp.id.desc()).all()
        return {"data": [serialize_app(a) for a in apps], "count": len(apps)}


@app.post("/applications/{app_id}/status")
def change_app_status(app_id: int, payload: StatusPayload, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    allowed = {"sent", "accepted", "rejected", "completed", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Недопустимый статус")
    with db_session() as s:
        a = s.get(DBApp, app_id)
        if not a:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        if user["role"] == "buyer" and a.buyer_id != user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа")
        if user["role"] == "supplier" and payload.status not in ("accepted", "rejected", "completed"):
            raise HTTPException(status_code=403, detail="Поставщик может только принять/отклонить/завершить")
        a.status = payload.status
        invoice = None
        if payload.status == "accepted" and not s.query(DBInvoice).filter_by(application_id=a.id).first():
            unit_price = (a.price / a.quantity) if a.quantity else a.price
            inv = DBInvoice(
                application_id=a.id, number=f"INV-{a.id:06d}",
                product=a.product, quantity=a.quantity, unit_price=unit_price,
                total=a.price, supplier_name=a.supplier_name, customer_name=a.customer,
            )
            s.add(inv); s.flush()
            invoice = serialize_invoice(inv)
        return {"status": "ok", "application": serialize_app(a), "invoice": invoice}


@app.get("/applications/{app_id}/invoice")
def get_invoice(app_id: int, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    with db_session() as s:
        a = s.get(DBApp, app_id)
        if not a:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        if user["role"] == "buyer" and a.buyer_id != user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа")
        inv = s.query(DBInvoice).filter_by(application_id=app_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Накладная отсутствует")
        return {"data": serialize_invoice(inv)}


@app.get("/suppliers/products")
def list_supplier_products(category: str = "", market: str = ""):
    with db_session() as s:
        q = s.query(SupplierProduct, User).join(User, User.id == SupplierProduct.supplier_id)
        if category: q = q.filter(SupplierProduct.category == category)
        if market: q = q.filter(SupplierProduct.market_type == market)
        items = []
        for p, u in q.order_by(SupplierProduct.id.desc()).limit(100).all():
            items.append({
                "id": p.id, "name": p.name, "category": p.category,
                "price": p.price, "market_type": p.market_type,
                "supplier_id": u.id, "supplier_name": u.username,
            })
        return {"data": items, "count": len(items)}


@app.post("/suppliers/products")
def add_supplier_product(payload: ProductPayload, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    if user["role"] != "supplier":
        raise HTTPException(status_code=403, detail="Только поставщик может добавлять товары")
    with db_session() as s:
        p = SupplierProduct(
            supplier_id=user["id"], name=payload.name, category=payload.category or "",
            price=payload.price, market_type=user.get("market_type", "retail"),
        )
        s.add(p); s.flush()
        return {"status": "ok", "id": p.id}


@app.delete("/suppliers/products/{pid}")
def del_supplier_product(pid: int, authorization: Optional[str] = Header(None)):
    user = require_user(authorization)
    with db_session() as s:
        p = s.get(SupplierProduct, pid)
        if not p or p.supplier_id != user["id"]:
            raise HTTPException(status_code=404, detail="Товар не найден")
        s.delete(p)
        return {"status": "ok"}


@app.get("/stats")
def stats(authorization: Optional[str] = Header(None)):
    user = get_user(authorization)
    with db_session() as s:
        total_users = s.query(User).count()
        total_apps = s.query(DBApp).count()
        my_apps = 0
        my_revenue = 0.0
        recent = []
        if user:
            if user["role"] == "buyer":
                qs = s.query(DBApp).filter_by(buyer_id=user["id"])
            else:
                qs = s.query(DBApp).filter((DBApp.supplier_id == user["id"]) | (DBApp.supplier_name.like(f"%{user['username']}%")))
            apps = qs.order_by(DBApp.id.desc()).all()
            my_apps = len(apps)
            my_revenue = sum(a.price for a in apps if a.status in ("accepted", "completed"))
            recent = [serialize_app(a) for a in apps[:5]]
        return {
            "total_users": total_users, "total_apps": total_apps,
            "my_apps": my_apps, "my_revenue": my_revenue, "recent": recent,
        }


@app.get("/health")
def health():
    return {"status": "ok"}


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"app": "AI Procurement Agent", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
