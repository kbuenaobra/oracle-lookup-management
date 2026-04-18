
# Oracle Lookup Management System - Technical Product Requirements Document

## 1. Executive Summary

This document outlines the technical requirements for an Oracle Lookup Management System—a web-based application designed to provide safe, auditable management of Oracle EBS lookup codes. The system enables users to search, maintain, and bulk-load lookup data while enforcing data integrity constraints and preventing unintended impacts on dependent modules.

---

## 2. Product Overview

### 2.1 Purpose
The Oracle Lookup Management System streamlines the creation, modification, and maintenance of lookup codes used throughout Oracle EBS environments. It provides:
- **Unified Search Interface** for rapid discovery of lookup codes across thousands of records
- **Safe CRUD Operations** with built-in data validation and audit trails
- **Dependency Impact Analysis** to prevent breaking active Concurrent Programs, Value Sets, and Reports
- **Bulk Data Import** capabilities for high-volume data migrations (FBDI-style)

### 2.2 Scope
- Management of FND_LOOKUP_TYPES and FND_LOOKUP_VALUES tables
- Real-time status indication based on effective dates and enabled flags
- CSV/Excel bulk upload with validation
- Cross-reference dependency tracking
- Audit column maintenance (CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)

---

## 3. Technical Stack

| Component | Technology |
|-----------|-----------|
| **Database** | Oracle Database 21c Express Edition (localhost:1521/XEPDB1) |
| **Backend Language** | Python 3.x with oracledb driver (Thin mode) |
| **Frontend Framework** | Streamlit (responsive web UI) |
| **Data Processing** | Pandas |
| **Database Driver** | oracledb (Thin mode) |

---

## 4. Database Schema

### 4.1 FND_LOOKUP_TYPES Table
```
Column Name          | Data Type        | Constraint | Description
--------------------|------------------|------------|----------------------------------
LOOKUP_TYPE          | VARCHAR2(30)     | PK         | Unique lookup type identifier
MEANING              | VARCHAR2(80)     | NOT NULL   | Display name for lookup type
DESCRIPTION          | VARCHAR2(240)    | NULL       | Additional documentation
CREATED_BY           | VARCHAR2(50)     | NOT NULL   | Audit - user who created record
CREATION_DATE        | DATE             | NOT NULL   | Audit - creation timestamp
LAST_UPDATED_BY      | VARCHAR2(50)     | NOT NULL   | Audit - user who last updated
LAST_UPDATE_DATE     | DATE             | NOT NULL   | Audit - last update timestamp
```

### 4.2 FND_LOOKUP_VALUES Table
```
Column Name          | Data Type        | Constraint | Description
--------------------|------------------|------------|----------------------------------
LOOKUP_TYPE          | VARCHAR2(30)     | PK, FK     | Reference to FND_LOOKUP_TYPES
LOOKUP_CODE          | VARCHAR2(30)     | PK         | Unique code within lookup type
MEANING              | VARCHAR2(80)     | NOT NULL   | Display value
DESCRIPTION          | VARCHAR2(240)    | NULL       | Additional documentation
ENABLED_FLAG         | VARCHAR2(1)      | NOT NULL   | 'Y' or 'N' (default: 'Y')
START_DATE_ACTIVE    | DATE             | NULL       | Effective start date
END_DATE_ACTIVE      | DATE             | NULL       | Effective end date
CREATED_BY           | VARCHAR2(50)     | NOT NULL   | Audit - user who created record
CREATION_DATE        | DATE             | NOT NULL   | Audit - creation timestamp
LAST_UPDATED_BY      | VARCHAR2(50)     | NOT NULL   | Audit - user who last updated
LAST_UPDATE_DATE     | DATE             | NOT NULL   | Audit - last update timestamp
```

---

## 5. Functional Requirements

### 5.1 Search & Discovery (The "Finder")

**FR-101: Global Search Capability**
- Implement a global search bar using SQL LIKE operators
- Support filtering by LOOKUP_TYPE or MEANING across thousands of records
- Display real-time results with minimal latency

**FR-102: Status Badges**
- Display visual badges indicating record status:
  - **Green Badge**: Active (ENABLED_FLAG = 'Y' AND current date between START_DATE_ACTIVE and END_DATE_ACTIVE)
  - **Red Badge**: Inactive (ENABLED_FLAG = 'N' OR current date outside effective date range)

---

### 5.2 Intelligent Maintenance (CRUD Operations)

**FR-201: Create Lookup Code**
- Provide sidebar form for adding individual codes
- Auto-populate ENABLED_FLAG with 'Y'
- Require LOOKUP_TYPE and LOOKUP_CODE (converted to uppercase)
- Set CREATED_BY and CREATION_DATE automatically
- Prevent duplicate LOOKUP_CODE entries within a LOOKUP_TYPE

**FR-202: Read Lookup Code**
- Display lookup codes in expander-based list
- Show status (Active/Inactive) with color-coded badges
- Status determined by ENABLED_FLAG and system date vs. effective dates
- Support sorting and filtering

**FR-203: Update Lookup Code**
- Allow inline editing of:
  - MEANING
  - DESCRIPTION
  - ENABLED_FLAG toggle ('Y' ↔ 'N')
  - START_DATE_ACTIVE and END_DATE_ACTIVE
- Prevent modification of:
  - LOOKUP_TYPE (after creation)
  - LOOKUP_CODE (after creation)
- Auto-update LAST_UPDATED_BY and LAST_UPDATE_DATE

**FR-204: Delete Lookup Code**
- **Permanent DELETE is DISABLED**
- Users may only:
  - Set END_DATE_ACTIVE to current date or earlier, OR
  - Toggle ENABLED_FLAG to 'N'
- Maintain full audit trail of all changes

---

### 5.3 Validation Logic

**FR-301: Date Range Validation**
- Ensure END_DATE_ACTIVE ≥ START_DATE_ACTIVE (when both are set)
- Display user-friendly error message if validation fails
- Prevent record save on validation failure

**FR-302: Case Normalization**
- Auto-convert LOOKUP_TYPE to uppercase
- Auto-convert LOOKUP_CODE to uppercase
- Allow MEANING and DESCRIPTION to retain case

**FR-303: Character Limit Validation**
- Enforce VARCHAR2 column limits during form input
- Provide real-time character count feedback

---

### 5.4 Dependency & Impact Analysis (The "Safety Net")

**FR-401: Cross-Reference View**
- Create a dedicated tab listing all dependent objects:
  - Concurrent Programs referencing the Lookup Type
  - Value Sets using the Lookup Type
  - Reports utilizing the Lookup Type
- Display reference names, ownership, and last-run dates (if applicable)

**FR-402: Impact Warning**
- Display pop-up alert if user attempts to disable or end-date a lookup currently used by an active Concurrent Program
- Include dependency name and affected module
- Provide option to proceed with warning acknowledged or cancel operation

---

### 5.5 Bulk Data Utility

**FR-501: File Upload Interface**
- Drag-and-drop interface for CSV/Excel file upload
- Accept .csv and .xlsx formats
- Display upload progress indicator

**FR-502: FBDI-Style Batch Processing**
- Use high-performance `executemany()` for batch inserts/updates
- Support single file containing multiple lookup types

**FR-503: Pre-Upload Validation**
- Check for duplicate LOOKUP_CODE entries within same LOOKUP_TYPE
- Verify overlapping effective dates within same code
- Ensure END_DATE_ACTIVE ≥ START_DATE_ACTIVE for all records
- Validate character limits before committing to database
- Identify required fields (LOOKUP_TYPE, LOOKUP_CODE, MEANING)

**FR-504: Transaction Handling**
- Atomic batch commit—all records succeed or none
- Rollback on any validation failure
- Display detailed error report on failure

---

## 6. Non-Functional Requirements

### 6.1 Performance
- **Search Performance**: Query results returned within 2 seconds for up to 10,000 records
- **Bulk Upload**: Process 5,000+ records per minute using batch execution
- **UI Responsiveness**: All page interactions complete within 1 second

### 6.2 Availability
- System available during normal business hours (target: 99% uptime)
- Graceful degradation if Oracle connection is unavailable

### 6.3 Security
- Database connection credentials stored securely (not in plaintext)
- User authentication required (integration with existing auth system TBD)
- Audit trail maintained for all DML operations
- No direct database access; all changes via application

### 6.4 Usability
- Responsive design supporting desktop and tablet views
- Keyboard navigation support
- Clear error messages with remediation guidance

### 6.5 Maintainability
- Code documented with inline comments
- Database schema documented in code repository
- Version control for all application and schema changes

---

## 7. Acceptance Criteria

| Requirement | Acceptance Criteria | Status |
|-------------|-------------------|--------|
| FR-101 | Global search filters 1,000+ records in < 2 seconds | Pending |
| FR-102 | Status badges display correctly for active and inactive records | Pending |
| FR-201 | New codes auto-populate ENABLED_FLAG = 'Y' | Pending |
| FR-202 | Records display with accurate status based on effective dates | Pending |
| FR-203 | LOOKUP_TYPE and LOOKUP_CODE remain read-only after creation | Pending |
| FR-204 | Permanent DELETE not available; soft delete via END_DATE_ACTIVE works | Pending |
| FR-301 | Date validation prevents END_DATE_ACTIVE < START_DATE_ACTIVE | Pending |
| FR-302 | All LOOKUP_TYPE and LOOKUP_CODE values stored in uppercase | Pending |
| FR-401 | Cross-reference tab shows dependent Concurrent Programs/Value Sets | Pending |
| FR-402 | Pop-up warning displays before disabling in-use lookup | Pending |
| FR-501 | Drag-and-drop CSV/Excel upload functions | Pending |
| FR-502 | Batch insert processes 5,000+ records per minute | Pending |
| FR-503 | Pre-upload validation catches duplicates and invalid dates | Pending |
| FR-504 | Transaction rollback on validation failure | Pending |

---

## 8. Out of Scope

- User authentication/authorization system (assume external provider)
- Multi-tenant support
- Real-time replication to other databases
- Mobile app (responsive web only)
- API/REST interface (initial version)

---

## 9. Dependencies & Risks

### 9.1 Technical Dependencies
- Oracle Database 21c+ with accessible FND_LOOKUP_TYPES and FND_LOOKUP_VALUES tables
- Python 3.8+
- Network connectivity to Oracle database

### 9.2 Known Risks
- **Risk**: Large bulk uploads may timeout if database is slow
  - **Mitigation**: Implement async batch processing with progress updates
- **Risk**: Soft deletes (END_DATE_ACTIVE) may confuse users vs. hard deletes
  - **Mitigation**: Clear UI labeling and help documentation
- **Risk**: Missing cross-references may lead to broken dependencies
  - **Mitigation**: Periodic audit reports comparing app references to actual code

---

## 10. Success Metrics

- Time to find a specific lookup code: < 10 seconds
- Reduction in manual SQL editing: > 80% of lookups managed via UI
- Zero data integrity issues (validated dates, case normalization)
- 100% audit trail compliance
- User satisfaction: > 4/5 rating

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-17 | Product Team | Initial PRD creation |
