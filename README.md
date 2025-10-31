# Garden State Grocery Gap (NJ)

**What it is:** A data-driven dashboard mapping grocery affordability across New Jersey ZIP codes.

**Data sources**
- U.S. Census ACS 2018–2022 5-year (median income, rent, home value)
- Walmart Grocery API (real data, cached monthly to control cost)
- USDA SNAP retailer density (per ZIP)

**Affordability score**
``(weekly basket cost ÷ monthly income) × 100``  
Categories: Green (high access) • Yellow (good) • Orange (moderate) • Red (at risk)

**Tech**
- Frontend: React + Tailwind (dark black/green theme)
- Backend: Python + MongoDB
- Tooling: Cursor, Emergent (for data refreshes & scripts)

**Run locally**
```bash
# frontend
cd frontend
npm install
npm start   # http://localhost:3000

