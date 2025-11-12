# Final-Web-Project

A web application built with FastAPI and MongoDB for managing products, orders, users, and more.

## Prerequisites

- Python 3.12 or higher
- MongoDB Atlas account (or local MongoDB instance)
- Virtual environment (`.venv`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/giangnhh23411/Final-Web-Project.git
cd Final-Web-Project-main
```

2. Create and activate virtual environment:
```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.\.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Activate the virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

2. Run the application:
```bash
python main.py
```

The server will start at `http://localhost:8000`

## Project Structure

```
Final-Web-Project-main/
├── main.py                 # FastAPI application entry point
├── Final-Web-Project-main/
│   ├── Assets/            # Static assets (CSS, JS, images)
│   ├── ClientSite/        # Client-facing HTML pages
│   ├── AdminSite/         # Admin panel HTML pages
│   └── index.html         # Main index page
├── mongodb/               # MongoDB scripts
└── requirements.txt       # Python dependencies
```

## API Endpoints

The API is available at `/api/` prefix. Main endpoints include:

- `/api/products` - Product management
- `/api/categories` - Category management
- `/api/users` - User management
- `/api/orders` - Order management
- `/api/carts` - Shopping cart
- `/api/vouchers` - Voucher management
- `/api/blogs` - Blog posts
- `/api/auth/login` - User login
- `/api/auth/register` - User registration

## Environment Variables

You can set the following environment variables:

- `MONGODB_URI` - MongoDB connection string (default: configured in main.py)
- `MONGODB_DB` - Database name (default: "plweb")
- `BASE_URL` - Base URL for uploads (default: "http://localhost:8000")

## Notes

- The application uses MongoDB Atlas by default
- Static files are served from `Final-Web-Project-main/Assets`, `Final-Web-Project-main/ClientSite`, and `Final-Web-Project-main/AdminSite`
- Make sure MongoDB connection is properly configured before running
