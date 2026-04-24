# Express Network - Email Connector Management

A polished web application for managing SMTP relays and OAuth conversions with Express Network branding.

## Features

- **Modern UI**: Clean, professional interface with Express Network corporate branding
- **Connector Management**: View and manage SMTP connectors and OAuth configurations
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Status**: Monitor connector status and configuration

## Getting Started

### Installation

```bash
npm install
```

### Development

```bash
# Build the frontend
npm run build

# Start the server
npm start

# Or use development mode with auto-reload
npm run dev
```

The application will be available at `http://localhost:3000`

### Production

```bash
npm run build
npm start
```

## Project Structure

```
emailer5000/
├── src/
│   ├── App.js          # Main React component
│   ├── App.css         # Styling with Express Network branding
│   └── index.js        # React entry point
├── public/
│   ├── index.html      # HTML template
│   └── bundle.js       # Built JavaScript (generated)
├── server.js           # Express server
├── webpack.config.js   # Webpack configuration
└── package.json        # Dependencies and scripts
```

## API Endpoints

- `GET /api/connectors` - Retrieve all email connectors
- `GET /api/health` - Health check endpoint

## Technologies

- **Frontend**: React 18, CSS3
- **Backend**: Express.js, Node.js
- **Build**: Webpack, Babel
- **Styling**: Custom CSS with Express Network color scheme (#0066CC)

## License

© 2026 Express Network. All rights reserved.
