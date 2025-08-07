# Deploy Mem0 Webhook to Railway

Your webhook server is ready to deploy! The GitHub repo has been created at:
https://github.com/quinnbmay/mem0-webhook

## Quick Deploy Steps:

1. **Go to Railway**: https://railway.app/new

2. **Deploy from GitHub repo**:
   - Click "Deploy from GitHub repo"
   - Select `quinnbmay/mem0-webhook`
   - Railway will auto-detect the Python app

3. **Set Environment Variables**:
   After deployment, go to Settings > Variables and add:
   ```
   MEM0_API_KEY=m0-IQGqsMWB42QhWG77RuzpSdNcyEppgRHeBhz0KcNu
   DEFAULT_USER_ID=quinn_may
   ```

4. **Get Your Webhook URL**:
   Once deployed, Railway will give you a URL like:
   `https://mem0-webhook-production.up.railway.app`

## Testing Your Webhook:

```bash
# Test the health endpoint
curl https://your-app.railway.app/health

# Create a memory via webhook
curl -X POST https://your-app.railway.app/webhook/memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Testing webhook deployment",
    "user_id": "quinn_may",
    "category": "test"
  }'
```

## Available Endpoints:

- `POST /webhook/memory` - Single memory creation
- `POST /webhook/memories/batch` - Batch memory creation
- `POST /webhook/zapier` - Zapier integration
- `POST /webhook/generic` - Any JSON payload
- `GET /health` - Health check

## Integration Examples:

### Zapier:
1. Create new Zap
2. Add Webhooks by Zapier action
3. Set URL: `https://your-app.railway.app/webhook/zapier`
4. Send test data

### n8n:
1. Add HTTP Request node
2. URL: `https://your-app.railway.app/webhook/memory`
3. Method: POST
4. Add JSON body with content

### Custom Integration:
```javascript
fetch('https://your-app.railway.app/webhook/memory', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    content: 'Memory from my app',
    user_id: 'quinn_may',
    category: 'automation'
  })
})
```

The server is configured and ready - just needs to be deployed via Railway dashboard!