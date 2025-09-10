# Contract Compliance & Transaction Monitoring System

## 📋 Overview

This system provides real-time contract compliance monitoring with AI-powered discrepancy detection. It monitors transactions against contract terms and flags compliance issues automatically.

## 🏗️ System Architecture

### Database Schema
- **contracts**: Contract metadata and parties
- **fees**: Static fee schedules from contracts  
- **transactions**: High-volume transaction data (100s per minute)
- **discrepancies**: AI-flagged compliance issues

### Components
- **Left Panel**: Contract Information (RAG-powered)
- **Center Panel**: Live Transaction Monitoring  
- **Right Panel**: AI Discrepancy Detection

## 🚀 Quick Setup

### 1. Database Setup
```bash
# Setup database tables with sample data
python scripts/setup_compliance_system.py
```

### 2. Manual Database Setup (Alternative)
```bash
# If you prefer manual setup
python scripts/generate_transaction_data.py --setup-db
```

### 3. Generate Test Data
```bash
# Generate 100 test transactions with discrepancies
python scripts/generate_transaction_data.py --batch 100

# Or continuous generation (120 transactions/minute)
python scripts/generate_transaction_data.py --continuous 120
```

### 4. Run the Application
```bash
python src/apps/main_app_full.py
```

## 📊 Sample Data Included

### Contracts
- **DBS-VISA-2020-001**: DBS Bank VISA Participation Agreement
- **DBS-MC-2021-001**: DBS Bank MasterCard Service Agreement  
- **PULSE-DBS-2020-ADD**: PULSE Network Access Addendum
- **AMEX-DBS-2021-002**: American Express Processing Agreement

### Fee Structures
- ATM withdrawal fees: $0.005 processing + $0.025 network
- Card payment fees: $0.150 processing + interchange rates
- International transaction fees: $1.50 cross-border + 1.2% conversion
- Fraud protection: Waived for DBS Bank

### Transaction Types
- `ATM_WITHDRAWAL`: ATM cash withdrawals
- `CARD_PAYMENT`: Point-of-sale transactions
- `INTERNATIONAL_TXN`: Cross-border transactions
- `BALANCE_INQUIRY`: Account balance checks
- `TRANSFER`: Fund transfers
- `CASH_ADVANCE`: Cash advances

## 🚨 Discrepancy Detection

The system automatically flags these compliance issues:

### Fee Mismatches
- **Overcharge**: Applied fee > Contract fee (e.g., $0.010 vs $0.005)
- **Undercharge**: Applied fee < Contract fee  
- **Missing Fee**: Required fee not applied
- **Extra Fee**: Unexpected fee applied
- **Wrong Fee Type**: Incorrect fee category

### Severity Levels
- **HIGH**: Missing required fees, significant overcharges (>$0.01)
- **MEDIUM**: Minor fee discrepancies (<$0.01)
- **LOW**: Fee type naming inconsistencies

## 💳 Transaction Generator Features

### Realistic Data Generation
- Merchant-specific transaction patterns
- Time-based transaction volumes
- Geographic transaction distribution
- Currency and amount variations

### Built-in Discrepancy Injection
- **8%** of transactions have fee overcharges
- **5%** have fee undercharges  
- **12%** missing required fees
- **3%** have unexpected extra fees
- **4%** have wrong fee types

### Usage Examples
```bash
# Setup everything at once
python scripts/setup_compliance_system.py

# Generate specific number of transactions
python scripts/generate_transaction_data.py --batch 500

# Continuous generation for testing
python scripts/generate_transaction_data.py --continuous 60

# Stop continuous generation with Ctrl+C
```

## 🔍 Using the System

### 1. Contract Information (Left Panel)
- Upload contract PDFs through RAG system
- Query contract terms: "What are the fee structures for DBS Bank?"
- View extracted contract details, parties, and terms

### 2. Transaction Monitoring (Center Panel)  
- View real-time transaction feed
- Adjust display limit (10-100 transactions)
- Monitor transaction amounts, fees, and timestamps
- Filter by merchant, type, or date range

### 3. Discrepancy Detection (Right Panel)
- Click "Check Now" to scan for compliance issues
- Enable "Auto-monitor" for continuous scanning
- View flagged transactions with explanations
- Review severity levels and resolution status

## 📈 Example Discrepancy Alerts

```
🚨 3 Discrepancies Found

🔴 HIGH SEVERITY (2):
- TXN_20240909_1234 (DBS BANK)
  Expected processing_fee: $0.005, but applied: $0.010
  Flagged: 14:25:30

- TXN_20240909_1235 (VISA)  
  Missing required network_fee: $0.025
  Flagged: 14:26:15

🟡 MEDIUM SEVERITY (1):
- TXN_20240909_1236 (MASTERCARD)
  Expected interchange_fee: $1.100, but applied: $1.050
  Flagged: 14:27:02
```

## 🔧 Configuration

### Database Connection
Set these environment variables:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_system
DB_USER=postgres
DB_PASSWORD=your_password
```

### Google AI Integration  
```bash
GOOGLE_API_KEY_SOL_4=your_google_api_key
```

## 📊 Database Queries

### Check Transaction Volume
```sql
SELECT COUNT(*), DATE(created_at) as date 
FROM transactions 
GROUP BY DATE(created_at) 
ORDER BY date DESC;
```

### Find Discrepancies
```sql
SELECT severity, COUNT(*) 
FROM discrepancies 
WHERE resolution_status = 'OPEN'
GROUP BY severity;
```

### Fee Compliance Rate
```sql
WITH compliance_check AS (
  SELECT t.transaction_id,
    CASE WHEN d.discrepancy_id IS NULL THEN 'COMPLIANT' ELSE 'NON_COMPLIANT' END as status
  FROM transactions t
  LEFT JOIN discrepancies d ON t.transaction_id = d.transaction_id
  WHERE t.created_at >= CURRENT_DATE - INTERVAL '7 days'
)
SELECT status, COUNT(*), 
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM compliance_check 
GROUP BY status;
```

## 🐛 Troubleshooting

### Database Connection Issues
```bash
# Test database connection
python -c "from src.components.database.db_analyzer import DatabaseAnalyzer; print(DatabaseAnalyzer().connection_status)"
```

### No Discrepancies Detected
- Ensure fees table has data: `SELECT COUNT(*) FROM fees;`
- Check transaction data: `SELECT COUNT(*) FROM transactions WHERE DATE(created_at) = CURRENT_DATE;`  
- Verify fee calculation logic in transaction generator

### Vector Store Issues
- Check FAISS index: Files should exist in `data/storage/faiss_db/`
- Reload contracts: Delete vector store and re-run setup

### Performance Optimization
- Index frequently queried columns
- Use connection pooling for high-volume inserts
- Consider partitioning transactions table by date

## 📚 Technical Details

### Transaction Generator Algorithm
1. **Load Expected Fees**: Query database for current fee schedules
2. **Generate Base Transaction**: Realistic amounts and merchant selection  
3. **Calculate Correct Fees**: Apply contract-based fee logic
4. **Inject Discrepancies**: Randomly modify fees based on error rates
5. **Insert to Database**: Store with applied fees for compliance checking

### Discrepancy Detection Logic
1. **Fetch Recent Transactions**: Get last N transactions from database
2. **Lookup Expected Fees**: Match merchant/transaction_type to fee table
3. **Compare Applied vs Expected**: Flag mismatches, missing fees, extra charges
4. **Severity Classification**: Categorize based on financial impact
5. **Generate Explanations**: AI-powered descriptions of compliance issues

---

**🎯 Ready to monitor contract compliance with AI-powered precision!**