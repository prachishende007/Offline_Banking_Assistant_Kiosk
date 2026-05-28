# Frontend (React + Vite)

This is the React frontend for AI Bank Assistance with voice interaction and EMI calculator.

## Features

- **Voice Assistant**: Multilingual voice interaction (English, Hindi, Marathi)
- **EMI Calculator**: Calculate loan EMIs with principal, interest rate, and tenure
- **Chat Interface**: Text-based banking queries
- **Responsive Design**: Works on desktop and mobile devices

## Local Setup

From project root:
```bash
cd frontend
npm install
npm run dev
```

App URL:
- `http://127.0.0.1:3000`

## Backend Requirement

The frontend expects backend APIs at `/api`.

In development, Vite proxy forwards `/api` to:
- `http://127.0.0.1:5000`

So run backend first:
```bash
python app.py
```

## Build
```bash
npm run build
npm run preview
```
