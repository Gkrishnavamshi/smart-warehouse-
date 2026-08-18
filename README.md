# Smart Warehouse Operations & Order Fulfillment System

Single-warehouse hackathon project for **WH-01 · Main Fulfillment Center**.

## Features
- Inventory & stock monitoring
- Low-stock / out-of-stock detection
- Priority-based order queue
- Inventory allocation with partial allocation logic
- Picking → Packing → Quality Check → Dispatch workflow
- Damaged item handling
- Exception → Decision → Resolution tracking
- Operational analytics and bottleneck indicators
- SQLite mock database with starter data

## Tech stack
- Frontend: React + Vite + Lucide React
- Backend: FastAPI + SQLAlchemy
- Database: SQLite

## Folder structure
```text
smart-warehouse/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── services/api.js
│       └── styles/app.css
└── README.md
```

## Windows / VS Code run steps

### 1) Install the prerequisites
Install these on your computer:
- Python 3.11+ (make sure **Add Python to PATH** is checked)
- Node.js 18+ (LTS is recommended)
- Visual Studio Code

Then restart VS Code after installing them.

### 2) Open the project
Extract the ZIP. In VS Code select **File → Open Folder** and choose the `smart-warehouse` folder.

### 3) Start the backend
Open VS Code terminal: **Terminal → New Terminal**.

Run:
```powershell
cd backend
py -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Keep this terminal running. You should see the FastAPI server on:
`http://127.0.0.1:8000`

### 4) Start the frontend
Open a **second** VS Code terminal with the `+` button.

Run:
```powershell
cd frontend
npm install
npm run dev
```

Vite will show a local URL such as:
`http://localhost:5173`

Ctrl+click that URL or copy it into Chrome.

### 5) Check the API
Open this in the browser:
`http://127.0.0.1:8000/docs`

This opens the automatic FastAPI API documentation.

## Important beginner notes
- Do **not** run both servers in the same terminal.
- Backend = terminal 1, frontend = terminal 2.
- When you see `(venv)` in terminal 1, the Python virtual environment is active.
- If you close the terminals, start them again with the commands above.
- The SQLite file `backend/warehouse.db` is created automatically the first time the backend starts.
- The project already contains sample products and sample orders, so you do not need an external API or real warehouse data.

## Reset demo data
Stop the backend, delete `backend/warehouse.db`, then start the backend again. The starter data will be recreated.

## Hackathon demo flow
1. Dashboard → explain decision engine and bottlenecks.
2. Inventory → show low-stock SKUs and damage handling.
3. Orders → click **Run allocation** on an order; shortage exceptions are generated automatically.
4. Fulfillment → complete Picking, then Packing, Quality Check, and Dispatch tasks.
5. Exceptions → resolve a shortage or damage exception.
6. Analytics → show status/category/stock-risk insights.

## Decision logic demonstrated
For an order requesting more units than are available:
1. Allocate the maximum safe quantity available.
2. Mark the order as `Partial` instead of pretending the order is fulfilled.
3. Create a `Stock Shortage` exception.
4. Keep the shortage traceable for an operator decision.
5. Low-stock products are flagged for replenishment based on `reorder_level` and `reorder_qty`.
