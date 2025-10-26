```mermaid
flowchart LR
  A[Address Input] --> B[Geoclient v2 (BBL)]
  B --> C[PLUTO (Socrata)]
  C --> D[Console Summary]
  A -->|optional| P[Foreclosure Parser PDFs]
  P --> D
