# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Server
```bash
python3 fhir_mcp_server.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

This is a Python-based MCP (Model Context Protocol) server that provides FHIR (Fast Healthcare Interoperability Resources) functionality. The entire implementation is contained in a single file: `fhir_mcp_server.py`.

### Key Components

1. **FHIRClient Class** (`fhir_mcp_server.py:45-120`): Async HTTP client that handles FHIR API interactions
   - Manages authentication via Bearer tokens
   - Implements retry logic for failed requests
   - Handles FHIR+JSON content type

2. **MCP Server Implementation** (`fhir_mcp_server.py:130-end`): Exposes FHIR functionality through MCP tools
   - Uses stdio for communication with MCP clients
   - Implements 11 tools: 
     - get_patient (retrieve specific patient by ID)
     - search_patients, search_all_patients (patient data)
     - search_observations (vital signs, lab values)
     - search_conditions (diagnoses)
     - search_medication_requests (prescriptions)
     - search_diagnostic_reports (lab reports)
     - search_care_plans (treatment plans)
     - get_capability_statement (server capabilities)
     - find_patients_with_conditions (find patient IDs from condition records)
     - assess_data_quality (evaluate server data quality and integrity)

### Environment Variables

- `FHIR_BASE_URL`: FHIR server endpoint (defaults to "https://hapi.fhir.org/baseR4")
- `FHIR_AUTH_TOKEN`: Optional Bearer token for authentication

### Dependencies

- `mcp>=0.1.0`: Model Context Protocol library
- `httpx>=0.25.0`: Async HTTP client
- `asyncio`: Built-in Python async support

### Development Notes

- The server communicates via stdio, so debugging output should use `file=sys.stderr`
- All FHIR operations are async and use httpx with a 30-second timeout
- The server supports pagination through the `_count` parameter in FHIR queries
- Enhanced error handling returns FHIR OperationOutcome resources for better error reporting
- Built-in data quality assessment detects orphaned references and data integrity issues
- Detailed logging shows request URLs and response metadata for debugging