# Order Generator - Web Application

**Version 1.0.0** - Initial Release

Web-based tool for copying existing orders in Manhattan WMS. Load an existing order, edit it, and create a new order with the modified data.

## Features

- ✅ **Authentication**: Secure token-based authentication with Manhattan WMS
- ✅ **Load Order**: Find and load existing orders by Order ID using the Search API
- ✅ **JSON Editor**: Syntax-highlighted JSON editor for viewing and editing order data
- ✅ **Create Order**: Create new orders by copying and modifying existing order data
- ✅ **Input Persistence**: Sample Order Number saved in localStorage
- ✅ **API Console**: Detailed console output showing all API calls and responses for testing
- ✅ **Comprehensive Logging**: Detailed API call logging in Vercel logs

## Setup Instructions

### 1. Environment Variables in Vercel

Add the following environment variables in your Vercel project settings:

#### Required:
- `MANHATTAN_PASSWORD` - Manhattan API password
- `MANHATTAN_SECRET` - Manhattan API client secret

### 2. Local Development

1. Install dependencies:
   ```bash
   npm install
   pip install -r requirements.txt
   ```

2. Set environment variables locally (create a `.env` file or export them):
   ```bash
   export MANHATTAN_PASSWORD="your_password"
   export MANHATTAN_SECRET="your_secret"
   ```

3. Run the development server:
   ```bash
   npm run dev
   # or
   vercel dev
   ```

### 3. Deployment

1. Connect your repository to Vercel
2. Add all environment variables in Vercel dashboard
3. Deploy!

## Usage

1. **Authenticate**: Enter ORG and click "Authenticate"
2. **Enter Order Number**: Enter the Order ID of an existing order you want to copy
3. **Load Order**: Click "Load Order" to retrieve the order data
4. **Edit Order**: Modify the JSON in the editor as needed (change OrderId, customer details, etc.)
5. **Create Order**: Click "Create Order" to create a new order with the modified data

## API Endpoints

- `POST /api/app_opened` - Track app open event
- `POST /api/auth` - Authenticate with Manhattan API
- `POST /api/find_order` - Find an order by Order ID using Search API
- `POST /api/create_order` - Create a new order using Order Save API

## API Details

### Find Order API
- **Endpoint**: `GET /search/api/search/order?query="'OrderId'='YOUR_ORDER_ID'"`
- **Purpose**: Retrieves order details for the specified Order ID
- **Note**: By default, only indexed fields are returned. Templates can be added later if more fields are needed.

### Create Order API
- **Endpoint**: `POST /order/api/order/order/save`
- **Purpose**: Creates a new order with the provided JSON payload
- **Payload**: Full order JSON structure (see sample in code)

## Project Structure

```
order_generator/
├── api/
│   ├── index.py          # Flask API endpoints
│   └── vercel.json       # Vercel configuration
├── index.html            # Frontend UI with CodeMirror editor
├── server.js             # Express server (for local dev)
├── package.json          # Node.js dependencies
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Features in Detail

### JSON Editor
- Uses CodeMirror for syntax highlighting
- Monokai theme for dark mode compatibility
- Line numbers and bracket matching
- Auto-close brackets and line wrapping

### API Console
- Shows all API requests and responses
- Color-coded messages (info, success, error)
- Timestamped entries
- Scrollable output
- Can be cleared for fresh testing

### Error Handling
- "Invalid Order" message if order not found
- JSON validation before creating orders
- Detailed error messages in console
- Status bar updates for user feedback

## Notes

- Sample Order Number is saved in browser localStorage
- ORG is never saved (security)
- All API calls are logged to Vercel logs for debugging
- Console output can be removed later if not needed
- The app is designed for copying existing orders - load, edit, create


