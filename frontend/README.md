# Strategos demo frontend

React 18 + Vite + TypeScript + Tailwind, connected to the FastAPI routes implemented in the parent workspace. The frontend uses the backend source as its API contract because the OpenAPI JSON block in the original brief was a placeholder.

## Run this scaffold

In PowerShell from the repository root:

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:5173`. The backend should be running at `http://127.0.0.1:8000`.

Set `VITE_API_BASE_URL` in `.env.local` to point at another backend, for example:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend polls `/health` and reports backend connectivity in the sidebar and top banner. Assessment IDs are kept in the route, so refreshes stay on the current assessment.

## Recreate the Vite shell from scratch

The supplied `frontend/` folder is already scaffolded. To create a separate starter app with the same stack:

```powershell
npm create vite@6 strategos-demo -- --template react-ts
cd strategos-demo
npm install
npm install react-router-dom@7.18.5 recharts lucide-react
npm install -D tailwindcss@3 postcss autoprefixer
```

Copy the supplied `src/` and Tailwind/PostCSS configuration into that new project, then add the `dev`, `build`, and `preview` scripts from `package.json`.

## Build

```powershell
npm run build
```

## Backend CORS

The parent FastAPI app is configured for both localhost hostnames on port 5173. If the API process predates that change, restart it. The exact middleware added in `app/main.py` is:

```python
application.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)
```

## Two-minute mentor demo

1. Open the workspace and wait for the green backend connection indicator.
2. Select **New assessment**, then **Load demo data**. The demo creates a sample patent JSON file locally; it is not a real patent document.
3. Continue to commercial details. Add annual revenue, revenue forecasts, a discount rate, and a royalty rate. Show the source badges changing to **User provided**. Leave other fields empty to demonstrate optional inputs.
4. Select **Start assessment**. The workflow view shows the patent profile feeding three parallel workstreams, with negotiation and report generation after their dependencies.
5. Open the report. Point out that valuation methods and the P10/P50/P90 simulation are calculated by deterministic Python, while patent, competitor, and claim chart outputs are visibly marked as placeholders.
6. Open **Edit / approve** on a reviewable section, add a short reviewer note, and record the review. Download the JSON report or use print/save as PDF.

## Next three improvements

1. Add document extraction and page-level evidence with a supported OCR/layout pipeline.
2. Connect commercial company datasets and retrieval/reranking so candidate targets and claim charts are evidence-backed.
3. Add dimension-level patent strength inputs, persistent saved drafts, and a true assessment history endpoint.
