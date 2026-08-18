# Kiosko POS - SaaS Edition 🛒

## 🎯 Project Summary

**The business problem:** "The store lost multiple hours a week in cash register closings and manual counting."
**The solution:** "Application built in Python with predictive analytics integration for stockout prevention."
**The impact:** "90% reduction in closing time and automation of debtor control."

---

## ✨ Key Features

* **Point of Sale (POS):** Fast sales with barcode scanner, charge by weight/quantity, and secure transaction handling.
* **Cash Control:** Cash register shifts, expense tracking, pre-calculated cash reconciliation, and detailed closings.
* **Current Accounts (Tabs):** Debtor management, partial payments, and inflation protection (debt valuation at today's prices).
* **Business Intelligence (BI):** Analytical dashboard to anticipate stockouts based on historical sales velocity.
* **Master Inventory:** Bulk price updates by category, shrinkage tracking, and Data Warehouse export to Excel.
* **SaaS Infrastructure:** Background cloud backups, security/licensing system (HWID), and auto-updater.
* **Productivity:** Floating widget for the cashier's quick notes.

## 🛠️ Technologies Used

* **Language:** Python 3
* **User Interface:** CustomTkinter / Tkinter
* **Database:** SQLite3 (Transactional)
* **Analysis & Export:** Pandas, OpenPyXL
* **Network Handling:** Requests (Auto-updater), Threading (Asynchronous backups)

## ⚙️ System Structure

* `main.py` - Entry point and main UI orchestrator.
* `database.py` - SQLite persistence engine and database schemas.
* `services.py` - Business logic (Inventory, Sales, Cash, Tabs, BI).
* `models.py` - Domain dataclasses (Product, Customer, Sale, etc.).
* `tab_*.py` - Controllers for the different views (Dashboard, Inventory, Tabs, Sales).
* `security.py` / `updater_service.py` / `backup_service.py` - Infrastructure modules.

## 🚀 Installation and Usage

1. Clone the repository.
2. Install the dependencies:
   ```bash
   pip install customtkinter pandas openpyxl requests
   ```
3. Run the main application:
   ```bash
   python main.py
   ```
