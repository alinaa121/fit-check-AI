# Wardrobe AI Frontend

A sleek, minimal Angular frontend for the Wardrobe AI application.

## Setup

1. **Install Node.js** (v18 or higher recommended)

2. **Install Angular CLI globally:**
   ```bash
   npm install -g @angular/cli
   ```

3. **Install dependencies:**
   ```bash
   cd web
   npm install
   ```

4. **Start the development server:**
   ```bash
   npm start
   ```
   
   The app will be available at `http://localhost:4200`

## Requirements

- Make sure your FastAPI backend is running at `http://localhost:8000`
- Backend should have CORS enabled (already configured in app.py)

## Features

- 🏠 **Welcome Page** - Elegant landing page with features overview
- 👔 **Wardrobe Gallery** - Grid view of all clothing items with AI metadata
- 🔍 **Item Details** - Detailed modal with comprehensive clothing information
- ⚡ **Fast Loading** - Optimized with lazy loading and efficient rendering
- 📱 **Responsive** - Works on desktop and mobile devices
- 🎨 **Minimal Design** - Clean, modern interface with smooth animations

## Structure

```
web/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   └── navbar/          # Navigation bar
│   │   ├── pages/
│   │   │   ├── welcome/         # Landing page
│   │   │   └── wardrobe/        # Wardrobe gallery
│   │   ├── services/
│   │   │   └── wardrobe.service.ts  # API service
│   │   └── app.routes.ts        # Routing configuration
│   ├── styles.css               # Global styles
│   └── index.html               # Main HTML
└── package.json                 # Dependencies
```

## Development

- Run `npm start` for dev server
- Navigate to `http://localhost:4200/`
- The app will automatically reload on code changes

## Build for Production

```bash
npm run build
```

Build artifacts will be stored in the `dist/` directory.
