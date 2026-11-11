# MindBridge frontend

React 19 with TypeScript, built by Vite and routed with React Router.

## Running

```bash
npm install
npm run dev        # http://localhost:3000
```

The app calls the Flask API at `http://127.0.0.1:5001/api/v1` by default. To use another address, set `VITE_API_URL` in a `.env.local` file in this folder.

## Scripts

- `npm run dev`: development server with hot reload.
- `npm run build`: type-check, then build to `dist/`.
- `npm run preview`: serve the production build locally.
- `npm run lint`: ESLint with the React Hooks and React Refresh rules.
