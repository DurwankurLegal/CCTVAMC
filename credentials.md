# CCTV SaaS Platform Credentials

Use the following credentials to log in, test, and validate the Module Subscription Framework, user roles, and platform settings.

## 🌟 Superadmin / Platform Admin

Use this account to access platform-admin level console management (managing SaaS plans, custom domain settings, and toggling business modules dynamically for any tenant).

* **Login URL**: [http://localhost:5174/](http://localhost:5174/)
* **Email**: `platform@durwankur.ai`
* **Password**: `Platform@1234`
* **Role**: Platform Administrator (is_platform_admin = True)
* **Master Tenant**: Durwankur Platform (`durwankur`)

---

## 🏢 Tenant Accounts (Companies A to E)

Each of the following companies has been provisioned with different optional subscription combinations to verify permissions gating, dynamic navigation filters, dashboards, reports, and document rendering.

**Global Password for all tenant accounts**: `Passw0rd@123`

### 1. Company A (Sales Only)
* **Subscribed Modules**: `Sales`, `Inventory` (AMC and Rental are disabled)
* **User Accounts**:
  * **Admin**: `admin@company-a.com`
  * **Billing / Accounts**: `billing@company-a.com`
  * **Technician**: `tech@company-a.com`

### 2. Company B (Rental Only)
* **Subscribed Modules**: `Rental`, `Assets` (Sales, AMC, and Inventory are disabled)
* **User Accounts**:
  * **Admin**: `admin@company-b.com`
  * **Billing / Accounts**: `billing@company-b.com`
  * **Technician**: `tech@company-b.com`

### 3. Company C (AMC Only)
* **Subscribed Modules**: `AMC`, `Assets` (Sales, Rental, and Inventory are disabled)
* **User Accounts**:
  * **Admin**: `admin@company-c.com`
  * **Billing / Accounts**: `billing@company-c.com`
  * **Technician**: `tech@company-c.com`

### 4. Company D (Sales and Rental)
* **Subscribed Modules**: `Sales`, `Rental`, `Inventory`, `Assets` (AMC is disabled)
* **User Accounts**:
  * **Admin**: `admin@company-d.com`
  * **Billing / Accounts**: `billing@company-d.com`
  * **Technician**: `tech@company-d.com`

### 5. Company E (All-in-One: Sales, Rental, and AMC)
* **Subscribed Modules**: `Sales`, `Rental`, `AMC`, `Inventory`, `Assets` (All modules enabled)
* **User Accounts**:
  * **Admin**: `admin@company-e.com`
  * **Billing / Accounts**: `billing@company-e.com`
  * **Technician**: `tech@company-e.com`
* **✨ Rich Seeded Datasets (Checkable)**:
  * **Products**: CCTV Dome Camera, CCTV Bullet Camera, 8-Ch NVR Hub, 1TB Surveillance HDD, 8-Port PoE Switch.
  * **Customers**: Gokuldham CHS (Society category), Apex Tech (Commercial), Corner Groceries (Single Shop).
  * **Inventory**: Stock trackers for dome/bullet cameras, HDDs, NVRs, and PoE switches.
  * **Sales transactions**: Approved Quotations, fulfilled Sales Orders, paid Invoices, UPI payments.
  * **Rental contracts**: 2 active recurring Rental Contracts with serialized Check-outs (`SR-COMPANY-E-NVR-5555`).
  * **AMC contracts**: Active AMC Contracts, open & resolved service tickets (with check-in/check-out logs, engineer work logs, and installations).
  * **Purchase Orders**: Received POs and partial NEFT payments to supplier.

---

## 🛠️ Verification Checklist

1. **Gated Navigation**: Dynamic sidebar filters hide links to unsubscribed business modules.
2. **Direct URL Protection**: Accessing an unsubscribed route via direct URL displays the `<ModuleGuard>` subscription upgrade prompt.
3. **API Gating**: Directly querying unsubscribed endpoints (e.g., hitting `/api/v1/amc/contracts` from `company-a`) returns `402 Payment Required`.
4. **Dashboard Gating**: Key KPI widgets return values only for subscribed modules; other widgets display zero.
5. **Reports catalog**: The `/api/v1/reports/catalogue` endpoint filters out reports requiring disabled modules.
