const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Mock API endpoint for connectors
// In production, this would connect to your actual database/service
app.get('/api/connectors', (req, res) => {
  // Mock data - replace with actual data source
  const mockConnectors = {
    value: [
      {
        name: 'Primary SMTP Relay',
        type: 'SMTP',
        host: 'smtp.expressnetwork.com',
        port: 587,
        status: 'active'
      },
      {
        name: 'OAuth Connector',
        type: 'OAuth 2.0',
        host: 'oauth.expressnetwork.com',
        port: 443,
        status: 'active'
      },
      {
        name: 'Backup Relay',
        type: 'SMTP',
        host: 'smtp-backup.expressnetwork.com',
        port: 587,
        status: 'active'
      }
    ]
  };

  res.json(mockConnectors);
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve React app for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Express Network Email Connector Management running on port ${PORT}`);
  console.log(`Visit http://localhost:${PORT} to view the application`);
});
