# AI Procurement Agent

Веб-приложение для поиска и анализа госзакупок Республики Казахстан.

---

## 🚀 Быстрый старт (с нуля)

### 1. Установите Python

Скачайте и установите Python:
https://www.python.org/downloads/

⚠️ ВАЖНО: при установке отметьте
**Add Python to PATH**

---

### 2. Клонируйте проект

```bash
git clone https://github.com/Assylzhan767/AI-Procurement-Agent-.git
cd AI-Procurement-Agent
```

---

### 3. Создайте виртуальное окружение

```bash
python -m venv venv
```

---

### 4. Активируйте окружение

#### Windows:

```bash
venv\Scripts\activate
```

Если PowerShell блокирует:

```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 5. Установите зависимости

```bash
pip install -r requirements.txt
```

---

### 6. Перейдите в папку backend

```bash
cd procurement
```

---

### 7. Исправьте импорт (ВАЖНО)

Откройте файл:

```
procurement/main.py
```

Найдите строку:

```python
from .db import db_session, User, Session as DBSession, Application as DBApp, Invoice as DBInvoice, SupplierProduct, hash_password, verify_password
```

Замените на:

```python
from db import db_session, User, Session as DBSession, Application as DBApp, Invoice as DBInvoice, SupplierProduct, hash_password, verify_password
```

---

### 8. Запустите сервер

```bash
uvicorn main:app --reload
```

---

### 9. Откройте приложение

Перейдите в браузере:

```
http://127.0.0.1:8000
```

---

## 📦 Стек технологий

* FastAPI — backend
* Uvicorn — сервер
* Requests — HTTP-запросы
* BeautifulSoup — парсинг HTML
* SQLAlchemy — база данных (SQLite)
* Vanilla JS — frontend

---

## ⚠️ Частые ошибки

### ❌ ModuleNotFoundError

Решение:

```bash
pip install <название_пакета>
```

---

### ❌ sqlalchemy / bs4 не найдено

Решение:

```bash
pip install sqlalchemy beautifulsoup4
```

---

### ❌ attempted relative import with no known parent package

Решение:

В `main.py` заменить:

```python
from .db import ...
```

на:

```python
from db import ...
```

---

## 💾 Рекомендуется

Тогда установка на новом устройстве:

```bash
pip install -r requirements.txt
```

---

## 🎯 Функционал

* Поиск лотов
* Загрузка данных с goszakup
* Фильтрация (в разработке)
* UI-интерфейс для работы с закупками

---

## 🧠 Автор 

Assylzhan

Проект разработан в рамках обучения и практики разработки веб-приложений.

---
